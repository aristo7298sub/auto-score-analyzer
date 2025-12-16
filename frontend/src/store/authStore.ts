import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: number;
  username: string;
  email: string;
  is_vip: boolean;
  vip_expires_at?: string | null;
  is_admin: boolean;
  quota_balance: number;
  quota_used: number;
  referral_code: string;
  referral_count: number;
  created_at: string;
  last_login: string | null;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (token: string, user: User) => {
        // 登录时清空成绩缓存（只保留新会话的数据）
        localStorage.removeItem('score-storage');
        // 同时清空 sessionStorage 标记
        sessionStorage.setItem('session-id', Date.now().toString());
        
        set({
          token,
          user,
          isAuthenticated: true,
        });
      },

      logout: () => {
        // 登出时清空成绩缓存
        localStorage.removeItem('score-storage');
        
        set({
          token: null,
          user: null,
          isAuthenticated: false,
        });
      },

      updateUser: (userData: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }));
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
