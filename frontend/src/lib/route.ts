import { useSyncExternalStore } from "react";

export type Route = "dashboard" | "tailor" | "applications" | "cvs" | "jobs" | "settings";

const ROUTES: readonly string[] = ["dashboard", "tailor", "applications", "cvs", "jobs", "settings"];

function read(): Route {
  const h = window.location.hash.replace(/^#\/?/, "");
  return ROUTES.includes(h) ? (h as Route) : "dashboard";
}

function subscribe(cb: () => void) {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
}

export const useRoute = (): Route => useSyncExternalStore(subscribe, read);

export const go = (route: Route) => { window.location.hash = `/${route}`; };
