const STORAGE_KEY = 'bud_owner_token';

export function getOwnerToken() {
  try {
    let token = localStorage.getItem(STORAGE_KEY);
    if (!token) {
      token = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, token);
    }
    return token;
  } catch {
    // Private browsing / storage blocked: fall back to a per-load token so requests still work,
    // just without surviving a reload.
    return crypto.randomUUID();
  }
}
