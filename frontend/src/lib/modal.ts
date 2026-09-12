/** Native modality for conditionally mounted overlays. The browser makes the
 * background inert; callers retain their existing cancel/close state handlers. */
export function modal(node: HTMLDialogElement) {
  const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  node.showModal();
  const close = node.querySelector<HTMLElement>('.ui-dialog__close, .close, .back-button, [data-dialog-close]');
  close?.focus({ preventScroll: true });
  return {
    destroy() {
      node.close();
      queueMicrotask(() => {
        if (opener?.isConnected && !document.querySelector('dialog:modal')) opener.focus({ preventScroll: true });
      });
    }
  };
}
