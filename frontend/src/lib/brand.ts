/**
 * Visible branding is build-time configuration. Technical storage, sessions
 * and API contracts deliberately do not use this value.
 */
export const APP_NAME = (import.meta.env.PUBLIC_APP_NAME || 'Cronicl').trim();
export const APP_INITIAL = APP_NAME.slice(0, 1).toUpperCase() || 'C';

export function pageTitle(section?: string): string {
  return section ? `${APP_NAME} – ${section}` : APP_NAME;
}
