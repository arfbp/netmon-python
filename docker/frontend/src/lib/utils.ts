import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merges class lists, resolving Tailwind class conflicts (e.g. two
 * conflicting padding utilities) in favor of the later one. Standard
 * shadcn/ui pattern — every component in components/ui/ uses this. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
