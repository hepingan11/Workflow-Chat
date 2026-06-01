import { spawn } from "node:child_process";

spawn("next", ["dev"], {
  env: {
    ...process.env,
    NEXT_DIST_DIR: ".next-dev",
  },
  shell: true,
  stdio: "inherit",
});
