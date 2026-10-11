import { apiClient } from "./apiClient";
import { LearningProgressData, ConceptProgress } from "@/types/progress";

export async function getUserProgress(): Promise<LearningProgressData> {
  return apiClient<LearningProgressData>("/users/me/progress");
}

export async function getConceptProgress(concept: string): Promise<ConceptProgress> {
  return apiClient<ConceptProgress>(`/users/me/progress/${encodeURIComponent(concept)}`);
}
