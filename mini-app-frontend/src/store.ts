import { create } from 'zustand';
import { Category, Tobacco, Mix, Stats, MixGenerateResponse } from './api';

interface AppState {
  // Data
  categories: Category[];
  tobaccos: Tobacco[];
  mixes: Mix[];
  favorites: Mix[];
  stats: Stats | null;
  
  // UI State
  isLoading: boolean;
  error: string | null;
  currentTab: 'home' | 'collection' | 'mix' | 'history' | 'favorites';
  
  // Current mix being displayed
  currentMix: MixGenerateResponse | null;
  
  // Actions
  setCategories: (categories: Category[]) => void;
  setTobaccos: (tobaccos: Tobacco[]) => void;
  addTobacco: (tobacco: Tobacco) => void;
  removeTobacco: (id: number) => void;
  clearTobaccos: () => void;
  
  setMixes: (mixes: Mix[]) => void;
  addMix: (mix: Mix) => void;
  updateMix: (mix: Mix) => void;
  
  setFavorites: (favorites: Mix[]) => void;
  
  setStats: (stats: Stats) => void;
  
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setCurrentTab: (tab: AppState['currentTab']) => void;
  
  setCurrentMix: (mix: MixGenerateResponse | null) => void;
}

export const useStore = create<AppState>((set) => ({
  // Initial state
  categories: [],
  tobaccos: [],
  mixes: [],
  favorites: [],
  stats: null,
  isLoading: false,
  error: null,
  currentTab: 'home',
  currentMix: null,
  
  // Actions
  setCategories: (categories) => set({ categories }),
  
  setTobaccos: (tobaccos) => set({ tobaccos }),
  addTobacco: (tobacco) => set((state) => ({ 
    tobaccos: [...state.tobaccos, tobacco].sort((a, b) => a.name.localeCompare(b.name))
  })),
  removeTobacco: (id) => set((state) => ({ 
    tobaccos: state.tobaccos.filter((t) => t.id !== id) 
  })),
  clearTobaccos: () => set({ tobaccos: [] }),
  
  setMixes: (mixes) => set({ mixes }),
  addMix: (mix) => set((state) => ({ mixes: [mix, ...state.mixes] })),
  updateMix: (mix) => set((state) => ({
    mixes: state.mixes.map((m) => (m.id === mix.id ? mix : m)),
    favorites: state.favorites.map((m) => (m.id === mix.id ? mix : m)),
  })),
  
  setFavorites: (favorites) => set({ favorites }),
  
  setStats: (stats) => set({ stats }),
  
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setCurrentTab: (currentTab) => set({ currentTab }),
  
  setCurrentMix: (currentMix) => set({ currentMix }),
}));
