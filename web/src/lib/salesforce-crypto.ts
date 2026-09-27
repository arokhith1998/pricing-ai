import "server-only";

import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { pricekeelSecret } from "@/lib/auth";

const VERSION = "v1";

function b64url(input: Buffer): string {
  return input.toString("base64url");
}

function fromB64url(input: string): Uint8Array<ArrayBuffer> {
  const source = Buffer.from(input, "base64url");
  const output = new Uint8Array(source.length);
  output.set(source);
  return output;
}

function encryptionSecret(): string {
  const value = process.env.SALESFORCE_TOKEN_ENCRYPTION_KEY?.trim();
  if (value) return value;
  if (process.env.VERCEL_ENV === "production") {
    throw new Error(
      "SALESFORCE_TOKEN_ENCRYPTION_KEY is required in production.",
    );
  }
  return `${pricekeelSecret()}:salesforce-dev-token-key`;
}

async function aesKey(): Promise<CryptoKey> {
  const digest = createHash("sha256").update(encryptionSecret()).digest();
  const bytes = new Uint8Array(digest.length);
  bytes.set(digest);
  return crypto.subtle.importKey("raw", bytes, "AES-GCM", false, [
    "encrypt",
    "decrypt",
  ]);
}

export async function encryptSalesforceSecret(value: string): Promise<string> {
  const iv = randomBytes(12);
  const plaintext = new TextEncoder().encode(value);
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    await aesKey(),
    plaintext,
  );
  return `${VERSION}.${b64url(iv)}.${b64url(Buffer.from(ciphertext))}`;
}

// Thrown instead of letting WebCrypto's own DOMException surface. AES-GCM
// decrypt fails the same opaque way ("The operation failed for an
// operation-specific reason") whether the ciphertext is corrupt or
// SALESFORCE_TOKEN_ENCRYPTION_KEY was rotated out from under a still-stored
// token; callers (connection/route.ts, workspace/route.ts) match on this
// class to answer with a clear, actionable 4xx instead of forwarding that
// text as a 502/503 (silent-failure-hunter finding 5).
export class SalesforceTokenDecryptionError extends Error {
  constructor(cause: unknown) {
    super(
      "Stored Salesforce tokens could not be decrypted. This usually means " +
        "SALESFORCE_TOKEN_ENCRYPTION_KEY was rotated after this org connected. " +
        "Reconnect the Salesforce org.",
    );
    this.name = "SalesforceTokenDecryptionError";
    this.cause = cause;
  }
}

export async function decryptSalesforceSecret(value: string): Promise<string> {
  const [version, ivRaw, ciphertextRaw] = value.split(".");
  if (version !== VERSION || !ivRaw || !ciphertextRaw) {
    throw new Error("Unsupported encrypted Salesforce secret format.");
  }
  let plaintext: ArrayBuffer;
  try {
    plaintext = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: fromB64url(ivRaw) },
      await aesKey(),
      fromB64url(ciphertextRaw),
    );
  } catch (cause) {
    throw new SalesforceTokenDecryptionError(cause);
  }
  return new TextDecoder().decode(plaintext);
}

function stateKey(): Buffer {
  return createHash("sha256")
    .update(`${pricekeelSecret()}:salesforce-oauth-state`)
    .digest();
}

export function signSalesforceState(payload: object): string {
  const encoded = b64url(Buffer.from(JSON.stringify(payload), "utf8"));
  const signature = createHmac("sha256", stateKey())
    .update(encoded, "utf8")
    .digest();
  return `${encoded}.${b64url(signature)}`;
}

export function verifySalesforceState<T>(value: string): T | null {
  const [encoded, suppliedRaw] = value.split(".");
  if (!encoded || !suppliedRaw) return null;
  const expected = createHmac("sha256", stateKey())
    .update(encoded, "utf8")
    .digest();
  let supplied: Uint8Array;
  try {
    supplied = fromB64url(suppliedRaw);
  } catch {
    return null;
  }
  if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
    return null;
  }
  try {
    return JSON.parse(Buffer.from(fromB64url(encoded)).toString("utf8")) as T;
  } catch {
    return null;
  }
}
