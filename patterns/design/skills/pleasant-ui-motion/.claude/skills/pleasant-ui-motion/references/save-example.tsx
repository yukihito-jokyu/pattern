import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";

// 両システムに存在するButtonのloadingだけを使う。保存処理は呼び出し側が渡す。
export function SaveExample({ save }: { save: () => Promise<void> }) {
  const [state, setState] = useState<"idle" | "pending" | "success" | "error">("idle");
  const pending = useRef(false);
  async function submit() {
    if (pending.current) return;
    pending.current = true;
    setState("pending");
    try { await save(); setState("success"); }
    catch { setState("error"); }
    finally { pending.current = false; }
  }
  const labels = { idle: "", pending: "保存中", success: "保存しました", error: "保存できませんでした。再試行できます" };
  return (
    <div>
      <Button loading={state === "pending"} onClick={() => { void submit(); }}>保存する</Button>
      <p role="status">{labels[state]}</p>
    </div>
  );
}
