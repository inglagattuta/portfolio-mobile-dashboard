import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const snapshotPath = path.join(root, "portfolio_snapshot.json");
const encryptedJsonPath = path.join(root, "encrypted_snapshot.json");
const encryptedJsPath = path.join(root, "encrypted_snapshot.js");

const passcode =
  process.env.PORTFOLIO_DASHBOARD_CODE ||
  process.argv.find((arg) => arg.startsWith("--code="))?.slice("--code=".length);

if (!passcode) {
  console.error("Missing code. Set PORTFOLIO_DASHBOARD_CODE or pass --code=...");
  process.exit(1);
}

const plaintext = await fs.readFile(snapshotPath, "utf8");
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const iterations = 250000;
const key = crypto.pbkdf2Sync(passcode, salt, iterations, 32, "sha256");
const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
const ciphertext = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
const tag = cipher.getAuthTag();

const payload = {
  version: 1,
  algorithm: "AES-256-GCM",
  kdf: "PBKDF2-SHA256",
  iterations,
  salt: salt.toString("base64"),
  iv: iv.toString("base64"),
  ciphertext: ciphertext.toString("base64"),
  tag: tag.toString("base64"),
};

const payloadJson = JSON.stringify(payload, null, 2);
await fs.writeFile(encryptedJsonPath, payloadJson, "utf8");
await fs.writeFile(
  encryptedJsPath,
  `window.ENCRYPTED_PORTFOLIO_SNAPSHOT = ${payloadJson};\n`,
  "utf8",
);

console.log(`Wrote ${encryptedJsonPath}`);
console.log(`Wrote ${encryptedJsPath}`);
