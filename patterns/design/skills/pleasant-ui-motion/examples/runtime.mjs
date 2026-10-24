// 動きと論理状態を分ける最小見本。デザインシステム本体の代替エンジンではない。
export function resolveMotion(parent, local, reduced) {
  return reduced ? "off" : local === "inherit" ? parent : local;
}

export function createSave(save, notify) {
  let pending = false;
  return async function submit() {
    if (pending) return;
    pending = true;
    notify("pending");
    try { await save(); notify("success"); }
    catch { notify("error"); }
    finally { pending = false; }
  };
}

export function createIndicator(element, readTiming, isEnabled) {
  let animation;
  function stop() { animation?.cancel(); animation = undefined; }
  function move(left) {
    // cancel後にliveなcomputed styleから読むと最終位置へ飛ぶため、値を先に保存する。
    const from = getComputedStyle(element).transform;
    stop();
    element.style.transform = `translateX(${left}px)`;
    const timing = readTiming();
    if (!isEnabled() || !element.animate || timing.duration <= 0) return;
    const next = element.animate([{ transform:from }, { transform:`translateX(${left}px)` }],timing);
    animation = next;
    void next.finished.then(
      () => { if (animation === next) animation = undefined; },
      () => { if (animation === next) animation = undefined; },
    );
  }
  return { move, stop };
}

// 論理状態は入力で変え、表示の補間はCSSへ任せる。終了イベントを操作の条件にしない。
export function createDisclosure(panel, trigger, labels) {
  let open = false;
  function setOpen(next) {
    open = next;
    if (!open && panel.contains(document.activeElement)) trigger.focus({ preventScroll:true });
    panel.inert = !open;
    panel.setAttribute("aria-hidden",String(!open));
    panel.dataset.open = String(open);
    trigger.setAttribute("aria-expanded",String(open));
    trigger.textContent = open ? labels.close : labels.open;
  }
  setOpen(false);
  return { toggle:() => setOpen(!open), close:() => setOpen(false) };
}
