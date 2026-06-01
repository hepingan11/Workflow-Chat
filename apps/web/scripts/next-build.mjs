import { spawn } from "node:child_process";

const child = spawn("next", ["build"], {
  env: {
    ...process.env,
    NEXT_DIST_DIR: ".next-build",
  },
  shell: true,
  stdio: "inherit",
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
