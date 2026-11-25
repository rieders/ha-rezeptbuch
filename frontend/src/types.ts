// Minimale Typen für das hass-Objekt und die Rezeptbuch-API.

export interface HassUser {
  id: string;
  name: string;
  is_admin: boolean;
}

export interface HomeAssistant {
  language: string;
  locale?: { language: string };
  user?: HassUser;
  themes?: { darkMode?: boolean };
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  fetchWithAuth?(path: string, init?: RequestInit): Promise<Response>;
  auth?: { data?: { access_token?: string }; accessToken?: string };
}

export interface PanelRoute {
  prefix: string;
  path: string;
}

export interface RecipeSummary {
  recipe_id: number;
  title: string;
  image_url: string | null;
  servings: number | null;
  prep_time: number | null;
  cook_time: number | null;
  total_time: number | null;
  avg_stars: number | null;
  rating_count: number;
  cooked_count: number;
  last_cooked: string | null;
  tags: string[];
  category_ids: number[];
}

export interface Ingredient {
  amount: number | null;
  amount_max: number | null;
  unit: string | null;
  name: string;
  note: string | null;
  group: string | null;
  quantity: string;
  text: string;
}

export interface Step {
  text: string;
  timer_seconds: number | null;
  group: string | null;
}

export interface VersionData {
  servings: number | null;
  servings_unit: string | null;
  prep_time: number | null;
  cook_time: number | null;
  total_time: number | null;
  ingredients: Ingredient[];
  steps: Step[];
}

export interface VersionInfo {
  id: number;
  version_no: number;
  label: string;
  is_original: boolean;
  is_default: boolean;
  change_note: string | null;
  user_name: string | null;
  created: string;
}

export interface Annotation {
  id: number;
  version_id: number | null;
  target_type: "recipe" | "ingredient" | "step";
  target_index: number | null;
  text: string;
  user_name: string | null;
  created: string;
}

export interface HistoryEntry {
  id: number;
  cooked_at: string | null;
  stars: number | null;
  comment: string | null;
  user_name: string | null;
  version_label: string | null;
  created: string;
}

export interface Category {
  id: number;
  parent_id: number | null;
  name: string;
  icon: string | null;
  color: string | null;
  count: number;
  count_total: number;
  children: Category[];
}

export interface CategoryTree {
  categories: Category[];
  uncategorized: number;
  total: number;
}

export interface Recipe {
  id: number;
  title: string;
  description: string | null;
  source_url: string | null;
  source_type: "url" | "photo" | "manual";
  image_url: string | null;
  default_version_id: number;
  version: { id: number; label: string; is_original: boolean; data: VersionData; original_servings: number | null };
  versions: VersionInfo[];
  categories: { id: number; name: string; path: string[] }[];
  tags: string[];
  images: { id: number; kind: string; url: string | null }[];
  annotations: Annotation[];
  stats: {
    avg_stars: number | null;
    rating_count: number;
    cooked_count: number;
    last_cooked: string | null;
    per_user: { user_id: string; user_name: string | null; avg_stars: number | null; rating_count: number }[];
  };
  history: HistoryEntry[];
}

export interface DiffEntry<T> {
  status: "unchanged" | "changed" | "added" | "removed";
  old: T | null;
  new: T | null;
  summary?: string;
  words?: { op: "equal" | "insert" | "delete"; text: string }[];
}

export interface VersionDiff {
  meta: { field: string; label: string; old: unknown; new: unknown }[];
  ingredients: DiffEntry<Omit<Ingredient, "quantity" | "text">>[];
  steps: DiffEntry<Step>[];
  has_changes: boolean;
}

export interface Draft {
  id: number;
  source_type: "url" | "photo" | "manual";
  created: string;
  title: string;
  description: string;
  source_url: string | null;
  image: string | null;
  images: { path: string; url: string | null }[];
  version: VersionData;
  ingredient_lines: string[];
  step_lines: string[];
  category_ids: number[];
  tags: string[];
  warnings: string[];
  similar_recipes: { id: number; title: string }[];
}

export interface PanelInfo {
  version: string;
  is_admin: boolean;
  default_servings: number;
  ai_task_available: boolean;
}

export interface ApiError {
  code: string;
  message: string;
}
