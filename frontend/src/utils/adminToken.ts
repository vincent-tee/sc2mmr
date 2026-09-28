const ADMIN_TOKEN_KEY = 'sc2mmr_admin_token';

export const hasAdminToken = (): boolean => {
  try {
    return Boolean(localStorage.getItem(ADMIN_TOKEN_KEY));
  } catch {
    return false;
  }
};

export const saveAdminToken = (token: string): boolean => {
  try {
    localStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
    return true;
  } catch {
    return false;
  }
};
