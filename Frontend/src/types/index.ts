/**
 * Types partagés (alignés avec l'API backend).
 */

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  created_at: string;
};
