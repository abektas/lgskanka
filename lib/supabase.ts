import { createClient, type SupabaseClient } from "@supabase/supabase-js";

function getSupabaseClient(): SupabaseClient | null {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  
  if (!supabaseUrl || !supabaseAnonKey) {
    return null;
  }
  
  return createClient(supabaseUrl, supabaseAnonKey);
}

let supabaseInstance: SupabaseClient | null = null;

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    if (!supabaseInstance) {
      supabaseInstance = getSupabaseClient();
    }
    if (!supabaseInstance) {
      throw new Error("Supabase not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY");
    }
    return (supabaseInstance as any)[prop];
  },
});

/** Profile types matching localStorage structure */
export interface SupabaseProfile {
  id: string;
  user_id: string;
  name: string;
  gender: "boy" | "girl";
  variant: number;
  registered_at: string;
  created_at: string;
  updated_at: string;
}

export interface SupabaseAnswerRecord {
  id: string;
  profile_id: string;
  question_id: string;
  subject: string;
  unit: number | null;
  unit_name: string | null;
  topic: string | null;
  selected_answer: string;
  correct: boolean;
  error_reason_code: string | null;
  time_spent_sec: number;
  created_at: string;
}

export interface SupabaseReinforcementTask {
  id: string;
  profile_id: string;
  subject: string;
  unit: number | null;
  unit_name: string | null;
  topic: string;
  source: string;
  wrong_count: number;
  created_at: string;
  question_ids: string[];
  answers: Record<string, string | null>;
  correctness: Record<string, boolean | null>;
  status: string;
  updated_at: string;
}

export interface SupabaseStudyStats {
  id: string;
  profile_id: string;
  total_solved: number;
  correct_count: number;
  streak_days: number;
  last_study_date: string | null;
  xp: number;
  updated_at: string;
}

export interface SupabaseGameProgress {
  id: string;
  profile_id: string;
  game_type: string;
  best_score: number;
  total_plays: number;
  updated_at: string;
}

export interface SupabaseBadgeProgress {
  id: string;
  profile_id: string;
  badge_id: string;
  earned: boolean;
  earned_at: string | null;
  progress: number;
  updated_at: string;
}