"""Answer schema and instruction shared by all single-call experiments."""
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["jump_change_is", "centile_change_reason", "noise_threshold_cm", "note"],
          "properties": {"jump_change_is": {"type": "string", "enum": ["real", "within_measurement_noise", "cannot_tell"]},
                         "centile_change_reason": {"type": "string", "enum": ["jump_change", "age_drift", "both", "none"]},
                         "noise_threshold_cm": {"type": "number"}, "note": {"type": "string"}}}
INSTR = ("\nReturn JSON with: jump_change_is (real | within_measurement_noise | cannot_tell), centile_change_reason "
         "(what mainly caused the centile change: jump_change | age_drift | both | none), noise_threshold_cm (the smallest "
         "change in cm you treated as a real change; 0 if you used none), note (at most 60 words, how the athlete is doing).")
SYSTEM = "You are assisting a strength and conditioning coach. Answer only with the requested JSON."
