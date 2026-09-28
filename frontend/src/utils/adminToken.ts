export const hasAdminToken = (): boolean => {
  try {
    return Boolean(localStorage.getItem('sc2mmr_admin_token'));
  } catch {
    return false;
  }
};
