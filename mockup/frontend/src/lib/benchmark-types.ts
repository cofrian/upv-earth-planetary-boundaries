export type ModelSummary = {
  model: string;
  top1_correct: number;
  top1_accuracy: number;
  top2_correct: number;
  top2_accuracy: number;
};

export type PerPbRow = {
  pb_code: string;
  n: number;
  specter_top1: number;
  scibert_top1: number;
  specter_top2: number;
  scibert_top2: number;
};

export type Agreement = {
  both_correct: number;
  only_specter: number;
  only_scibert: number;
  both_wrong: number;
};

export type DiscordanceExample = {
  doc_id: string;
  gt: string;
  specter_pred: string;
  scibert_pred: string;
  specter_score: number;
};

export type BackboneRow = {
  model: string;
  mode: string;
  micro_f1: number;
  macro_f1: number;
  lrap: number;
};

export type HumanModelSummary = {
  model: string;
  n_evaluated: number;
  top1_in_gold_correct: number;
  top1_in_gold_accuracy: number;
  top12_in_gold_correct: number;
  top12_in_gold_accuracy: number;
};

export type HumanAgreement = {
  n_paired: number;
  both_top1_correct: number;
  only_specter_top1: number;
  only_scibert_top1: number;
  both_top1_wrong: number;
};

export type HumanExample = {
  doc_id: string;
  gold: string;
  specter_pred: string;
  scibert_pred: string;
  specter_score: number;
  specter_ok: boolean;
  scibert_ok: boolean;
};

export type HumanValidation =
  | {
      available: false;
    }
  | {
      available: true;
      n_papers_total: number;
      n_specter_evaluated: number;
      n_scibert_evaluated: number;
      n_both_evaluated: number;
      n_uncovered: number;
      avg_gold_labels_per_paper: number;
      models: HumanModelSummary[];
      agreement: HumanAgreement;
      examples: HumanExample[];
    };

export type ModelsBenchmark = {
  available: boolean;
  n_papers: number;
  ground_truth?: string;
  models: ModelSummary[];
  per_pb: PerPbRow[];
  agreement: Agreement;
  discordance_examples: {
    only_specter: DiscordanceExample[];
    only_scibert: DiscordanceExample[];
  };
  backbones_table: BackboneRow[];
  human_validation: HumanValidation;
};
