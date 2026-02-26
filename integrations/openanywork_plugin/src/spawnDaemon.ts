import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";

export type DaemonInfo = {
  port: number;
  token: string;
  base_url: string;
};

export function spawnDaemon(exePath: string): Promise<{ proc: ChildProcessWithoutNullStreams; info: DaemonInfo }> {
  return new Promise((resolve, reject) => {
    const proc = spawn(exePath, [], { stdio: ["ignore", "pipe", "pipe"] });

    let settled = false;
    proc.stdout.once("data", (chunk: Buffer) => {
      if (settled) return;
      settled = true;
      try {
        const info = JSON.parse(chunk.toString("utf8").trim()) as DaemonInfo;
        resolve({ proc, info });
      } catch (error) {
        reject(error);
      }
    });

    proc.once("error", (error) => {
      if (settled) return;
      settled = true;
      reject(error);
    });
  });
}
