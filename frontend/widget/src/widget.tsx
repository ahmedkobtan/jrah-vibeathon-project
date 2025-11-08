import React from 'react';
import ReactDOM from 'react-dom/client';

import { WidgetApp } from './WidgetApp';
import './style.css';

const mountedRoots = new WeakMap<HTMLElement, ReactDOM.Root>();

type MountOptions = {
  apiBase?: string;
};

declare global {
  interface Window {
    TransparentCareWidget?: {
      mount: (container: HTMLElement, options?: MountOptions) => void;
      unmount: (container: HTMLElement) => void;
    };
  }
}

function ensureRoot(container: HTMLElement) {
  let root = mountedRoots.get(container);
  if (!root) {
    root = ReactDOM.createRoot(container);
    mountedRoots.set(container, root);
  }
  return root;
}

function mount(container: HTMLElement, _options?: MountOptions) {
  const root = ensureRoot(container);
  root.render(
    <React.StrictMode>
      <WidgetApp />
    </React.StrictMode>
  );
}

function unmount(container: HTMLElement) {
  const root = mountedRoots.get(container);
  if (root) {
    root.unmount();
    mountedRoots.delete(container);
  }
}

if (typeof window !== 'undefined') {
  window.TransparentCareWidget = { mount, unmount };
}

export { mount, unmount };
