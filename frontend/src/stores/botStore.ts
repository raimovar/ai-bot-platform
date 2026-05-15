// Bot store using Zustand

import { create } from 'zustand';
import type { Bot } from '../types';

interface BotState {
  bots: Bot[];
  currentBot: Bot | null;
  isLoading: boolean;
  
  setBots: (bots: Bot[]) => void;
  addBot: (bot: Bot) => void;
  updateBot: (id: string, updates: Partial<Bot>) => void;
  removeBot: (id: string) => void;
  setCurrentBot: (bot: Bot | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useBotStore = create<BotState>((set) => ({
  bots: [],
  currentBot: null,
  isLoading: false,
  
  setBots: (bots) => set({ bots }),
  
  addBot: (bot) => set((state) => ({
    bots: [bot, ...state.bots]
  })),
  
  updateBot: (id, updates) => set((state) => ({
    bots: state.bots.map((b) => 
      b.id === id ? { ...b, ...updates } : b
    ),
    currentBot: state.currentBot?.id === id 
      ? { ...state.currentBot, ...updates } 
      : state.currentBot
  })),
  
  removeBot: (id) => set((state) => ({
    bots: state.bots.filter((b) => b.id !== id),
    currentBot: state.currentBot?.id === id ? null : state.currentBot
  })),
  
  setCurrentBot: (bot) => set({ currentBot: bot }),
  
  setLoading: (loading) => set({ isLoading: loading }),
}));
