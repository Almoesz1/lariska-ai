export type NegotiationResponse = {
  suggested_reply: string;
  decision_result: {
    final_action: "hold_price" | "discount" | "bonus" | "counter_offer";
    final_price: number;
    applied_discount_pct: number;
    ml_confidence: number;
    floor_price_locked: boolean;
    guard_reason: string;
  };
  emotion_info: {
    emotion: string;
    confidence: number;
    tone_hint: string;
  };
};
