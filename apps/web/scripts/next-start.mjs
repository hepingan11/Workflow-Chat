import { spawn } from "node:child_process";

spawn("next", ["start"], {
  env: {
    ...process.env,
    NEXT_DIST_DIR: ".next-build",
  },
  shell: true,
  stdio: "inherit",
});
