import { create } from 'zustand';
import { User } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (token: string, user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

const TOKEN_KEY = 'bridge_access_token';
const USER_KEY = 'bridge_user';

const getInitialUser = (): User | null => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const useAuthStore = create<AuthState>((set) => {
  const initialUser = getInitialUser();
  const initialToken = localStorage.getItem(TOKEN_KEY);

  return {
    user: initialUser,
    token: initialToken,
    isAuthenticated: !!initialToken || !!initialUser,
    isLoading: !initialUser && !!initialToken,

    setUser: (user) => {
      if (user) {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      } else {
        localStorage.removeItem(USER_KEY);
      }
      set({ user, isAuthenticated: !!user });
    },

    setToken: (token) => {
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
      set({ token, isAuthenticated: !!token });
    },

    login: (token, user) => {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ token, user, isAuthenticated: true, isLoading: false });
    },

    logout: () => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({ token: null, user: null, isAuthenticated: false, isLoading: false });
    },

    setLoading: (loading) => set({ isLoading: loading }),
  };
});

