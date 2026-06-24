/**
 * 前端类型定义，对齐后端 Pydantic schema（backend/quizcraft/schemas/）。
 *
 * 切片 1.1 答题视图只消费题面（stem/options）+ source_span，不渲染 correct_option_index，
 * 防止正确答案下标泄露——前端代码对 correct_option_index 取而不显示。
 */

export interface SourceSpan {
  page: number | null;
  section_path: string;
  text: string;
}

export interface SectionOut {
  id: number;
  section_path: string;
  page_number: number;
  token_count: number | null;
  order_index: number;
  content: string;
}

export interface DocumentDetail {
  id: number;
  filename: string;
  page_count: number | null;
  status: string;
  section_count: number;
  created_at: string | null;
  sections: SectionOut[];
}

export interface ConceptOut {
  id: number;
  name: string;
  description: string | null;
  source_span: SourceSpan;
  bloom_level: string | null;
}

export interface QuestionOut {
  id: number;
  concept_id: number | null;
  section_id: number | null;
  question_type: string;
  stem: string;
  options: string[];
  /** 后端返回正确答案下标；答题视图刻意不渲染，防泄露。 */
  correct_option_index: number | null;
  answer_text: string | null;
  explanation: string | null;
  source_span: SourceSpan;
  bloom_level: string | null;
  difficulty: string | null;
  self_eval_score: number | null;
  is_flagged: boolean;
  in_practice_pool: boolean;
}

export interface QuizSessionOut {
  id: number;
  document_id: number;
  question_ids: number[];
  status: string;
  score: number | null;
  total: number | null;
  created_at: string | null;
}

export interface QuizGenerationResponse {
  quiz_session: QuizSessionOut;
  questions: QuestionOut[];
  concepts: ConceptOut[];
}

export interface QuizGenerationRequest {
  number?: number;
  difficulty_range?: string[];
  question_types?: string[];
  chapter_scope?: string[];
  bloom_distribution?: Record<string, number>;
  concepts_per_section?: number;
  questions_per_concept?: number;
  self_eval_threshold?: number;
  auto_publish?: boolean;
}

export type DraftQuizGenerationRequest = Omit<QuizGenerationRequest, "auto_publish">;

export interface AnswerOut {
  id: number;
  quiz_session_id: number;
  question_id: number;
  selected_option_index: number | null;
  short_answer_text: string | null;
  is_correct: boolean | null;
  score: number | null;
  feedback: string | null;
}

export interface QuestionUpdateRequest {
  stem?: string;
  options?: string[];
  correct_option_index?: number;
  answer_text?: string;
  explanation?: string;
}
