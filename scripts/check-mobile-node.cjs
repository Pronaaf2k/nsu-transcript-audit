"use strict";

const major = Number(process.versions.node.split(".")[0]);

if (Number.isNaN(major)) {
  console.error("Could not detect Node.js version.");
  process.exit(1);
}

if (major < 20 || major >= 24) {
  console.error(
    [
      "Unsupported Node.js version for Expo SDK 50 mobile app.",
      `Detected: ${process.versions.node}`,
      "Required: >=20 and <24",
      "Please switch to Node 20 LTS and retry: pnpm dev:mobile",
    ].join("\n")
  );
  process.exit(1);
}
