import pytest

from src.config import (
    S2_SYSTEM_PROMPT_PATH,
    _validate_prompt_content,
    clear_prompt_cache,
    get_s2_prompt,
    validate_prompt_files,
)


def _full_s2_contract_prompt(*, omit: tuple[str, ...] = ()) -> str:
    field_lines = [
        ('"intention"', '{ "label": "...", "confidence": 0.0 }'),
        ('"defensiveness_score"', "0.0"),
        ('"defensiveness_markers"', "[]"),
        ('"danger_level"', "0\n      # levels: 0, 1, 2, 3"),
        ('"danger_signals"', "[]"),
        ('"themes_latents"', "[]"),
        ('"loop_detected"', "false"),
        ('"loop_theme"', "null"),
        ('"loop_count"', "0"),
        (
            '"correlation"',
            'null\n      # otherwise: { "hypothesis": "...", "confidence": 0.0 }',
        ),
        ('"ipc_position"', '{ "agency": 0.0, "communion": 0.0 }'),
        ('"axis_crossing"', "false"),
        ('"sycophancy_risk"', "0.0"),
        ('"fanfaronade_score"', "0.0"),
        ('"cold_weaver_topics"', "[]"),
        (
            '"recurring_minor_elements"',
            """[
        {
          "content": "...",
          "type": "in_joke",
          "count": 2,
          "importance": 0.2,
          "user_reaction": "amused"
        }
      ]
      # type: in_joke, object_callback, ritual, theme
      # user_reaction: neutral, engaged, amused, callback""",
        ),
        ('"trigger_description"', '"..."'),
        ('"recommended_H_delta"', '0.0\n      # range: -0.5 to +0.5'),
        (
            '"recommended_phase"',
            'null\n      # phases: probing, silent, reflection, sparring',
        ),
    ]
    rendered_fields = [
        f"      {field}: {value}"
        for field, value in field_lines
        if field.strip('"') not in omit
    ]
    return "{\n" + ",\n".join(rendered_fields) + "\n    }\n"


@pytest.fixture(autouse=True)
def prompt_cache():
    clear_prompt_cache()
    yield
    clear_prompt_cache()


def test_validate_s2_prompt_requires_recurring_minor_elements_contract_tokens():
    content = _full_s2_contract_prompt()

    _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_recurring_minor_element_fields():
    content = _full_s2_contract_prompt().replace(
        '"type": "in_joke",\n          "count": 2,\n          "importance": 0.2,\n          "user_reaction": "amused"\n',
        "",
    )

    with pytest.raises(ValueError, match="missing required contract token"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_intention_nested_fields():
    content = _full_s2_contract_prompt().replace(
        '{ "label": "...", "confidence": 0.0 }',
        '{"label": "..."}',
    )

    with pytest.raises(ValueError, match="confidence"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_ipc_position_nested_fields():
    content = _full_s2_contract_prompt().replace(
        '{ "agency": 0.0, "communion": 0.0 }',
        '{"agency": 0.0}',
    )

    with pytest.raises(ValueError, match="communion"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_intention_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    Padding sentence one adds enough unrelated words to exceed the local grouped
    contract search window for the nested intention fields.
    Padding sentence two keeps describing style, tone, examples, formatting,
    analysis depth, response cadence, and internal bookkeeping without defining
    the nested object shape nearby.
    Padding sentence three keeps the gap large with extra vocabulary about
    placeholders, examples, summaries, adapters, parsers, validators, and logs.

    Appendix:
    label confidence

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="label|confidence"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_ipc_position_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    Padding sentence one adds enough unrelated words to exceed the local grouped
    contract search window for the nested ipcPosition fields.
    Padding sentence two keeps describing style, tone, examples, formatting,
    analysis depth, response cadence, and internal bookkeeping without defining
    the nested object shape nearby.
    Padding sentence three keeps the gap large with extra vocabulary about
    placeholders, examples, summaries, adapters, parsers, validators, and logs.

    Appendix:
    agency communion

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="agency|communion"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_recurring_minor_element_enum_tokens():
    content = _full_s2_contract_prompt().replace(
        '# type: in_joke, object_callback, ritual, theme\n'
        '      # user_reaction: neutral, engaged, amused, callback',
        "",
    )

    with pytest.raises(
        ValueError,
        match="object_callback|ritual|theme|neutral|engaged|callback",
    ):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_recurring_entry_fields_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    This paragraph adds unrelated contract prose, examples, and placeholders so
    the recurring entry schema cannot be satisfied by distant appendix tokens.
    Another sentence continues padding the gap with descriptions of formatting,
    summaries, adapters, validators, logging, reasoning depth, and examples.
    A third sentence adds extra unrelated words about personas, state machines,
    fallbacks, parsers, confidence scores, and diagnostic metadata.

    Appendix:
    content type count importance userReaction

    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="content|type|count|importance|user_reaction"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_recurring_entry_enum_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    This paragraph adds unrelated contract prose, examples, and placeholders so
    the recurring enum contract cannot be satisfied by distant appendix tokens.
    Another sentence continues padding the gap with descriptions of formatting,
    summaries, adapters, validators, logging, reasoning depth, and examples.
    A third sentence adds extra unrelated words about personas, state machines,
    fallbacks, parsers, confidence scores, and diagnostic metadata.

    Appendix:
    inJoke objectCallback ritual theme neutral engaged amused callback

    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(
        ValueError,
        match="in_joke|object_callback|ritual|theme|neutral|engaged|amused|callback",
    ):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_danger_level_enum_tokens():
    content = _full_s2_contract_prompt().replace(
        '\n      # levels: 0, 1, 2, 3',
        "",
    )

    with pytest.raises(ValueError, match="1|2|3"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_correlation_fields():
    content = _full_s2_contract_prompt().replace(
        '"correlation": null\n      # otherwise: { "hypothesis": "...", "confidence": 0.0 }',
        '"correlation": null\n      # otherwise: { "hypothesis": "..." }',
    )

    with pytest.raises(ValueError, match="confidence"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_recommended_h_delta_range_tokens():
    content = _full_s2_contract_prompt().replace(
        '\n      # range: -0.5 to +0.5',
        "",
    )

    with pytest.raises(ValueError, match="-0.5|\\+0.5"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_correlation_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    Padding sentence one adds enough unrelated words to exceed the local grouped
    contract search window for this field.
    Padding sentence two keeps describing style, tone, examples, formatting,
    analysis depth, response cadence, and internal bookkeeping without defining
    the object shape nearby.
    Padding sentence three keeps the gap large with extra vocabulary about
    placeholders, examples, summaries, adapters, parsers, validators, and logs.

    Appendix:
    null hypothesis confidence

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    dangerLevel accepts 0, 1, 2, and 3.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="null|hypothesis|confidence"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_recommended_phase_enum_tokens():
    content = _full_s2_contract_prompt().replace(
        '\n      # phases: probing, silent, reflection, sparring',
        "",
    )

    with pytest.raises(ValueError, match="probing|silent|reflection|sparring"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_recommended_phase_null_contract():
    content = _full_s2_contract_prompt().replace(
        ': null\n      # phases: probing, silent, reflection, sparring',
        ': "sparring"\n      # phases: probing, silent, reflection, sparring',
    )

    with pytest.raises(ValueError, match="null"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_recommended_phase_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    Padding sentence one adds enough unrelated words to exceed the local grouped
    contract search window for this field.
    Padding sentence two keeps describing style, tone, examples, formatting,
    analysis depth, response cadence, and internal bookkeeping without defining
    the allowed values nearby.
    Padding sentence three keeps the gap large with extra vocabulary about
    placeholders, examples, summaries, adapters, parsers, validators, and logs.

    Appendix:
    null probing silent reflection sparring

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    dangerLevel accepts 0, 1, 2, and 3.
    """

    with pytest.raises(ValueError, match="null|probing|silent|reflection|sparring"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_recommended_h_delta_range_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    Padding sentence one adds enough unrelated words to exceed the local grouped
    contract search window for this field.
    Padding sentence two keeps describing style, tone, examples, formatting,
    analysis depth, response cadence, and internal bookkeeping without defining
    the numeric range nearby.
    Padding sentence three keeps the gap large with extra vocabulary about
    placeholders, examples, summaries, adapters, parsers, validators, and logs.

    Appendix:
    -0.5 +0.5

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="-0.5|\\+0.5"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_danger_level_tokens_far_from_anchor():
    content = """
    Produce an object with intention, defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.

    This paragraph adds unrelated contract prose, examples, and placeholders so
    the numeric enum check cannot be satisfied by distant appendix tokens.
    Another sentence continues padding the gap between the field list above and
    any later mention of the allowed integers as an unrelated appendix list.
    A third sentence adds extra unrelated words about formatting, summaries,
    adapters, validators, schemas, confidence scores, and logging details.

    Appendix:
    0 1 2 3

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    RecommendedPhase accepts null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="1|2|3"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_accepts_case_insensitive_prose_contract_tokens():
    content = """
    Analyse la conversation et produis un objet avec INTENTION,
    intention label, intention confidence,
    defensiveness score, defensiveness markers, DANGER_LEVEL,
    danger signals, themes latents, loop detected, loop theme,
    loop count, correlation, ipc position, agency, communion, axis crossing,
    sycophancy risk, fanfaronade score, cold weaver topics,
    recommended h delta, recurring minor elements,
    trigger description et recommended phase.
    DANGER_LEVEL accepte 0, 1, 2 et 3.
    correlation accepte NULL ou un objet avec HYPOTHESIS et CONFIDENCE.
    recommended h delta accepte une plage de -0.5 a +0.5.

    Pour recurring minor elements, chaque entree doit inclure CONTENT, type, count,
    importance et USER REACTION. Type accepte IN JOKE, OBJECT CALLBACK,
    ritual et theme. User reaction accepte neutral, engaged, amused et callback.
    Recommended phase accepte NULL, PROBING, SILENT, REFLECTION et SPARRING.
    """

    _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_accepts_unicode_minus_in_recommended_h_delta_range():
    content = """
    Produce an object with intention, intentionLabel, intentionConfidence,
    defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, agency, communion, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    recommendedHDelta accepts values from −0.5 to +0.5.

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    Valid recommendedPhase values are null, probing, silent, reflection, and sparring.
    """

    _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_unicode_minus_without_positive_recommended_h_delta_bound():
    content = """
    Produce an object with intention, intentionLabel, intentionConfidence,
    defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, agency, communion, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    recommendedHDelta accepts values from −0.5.

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    Valid recommendedPhase values are null, probing, silent, reflection, and sparring.
    """

    with pytest.raises(ValueError, match="\\+0.5"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_accepts_hyphenated_contract_tokens():
    content = """
    intention, intention-label, intention-confidence, defensiveness-score,
    defensiveness-markers, danger-level,
    danger-signals, themes-latents, loop-detected, loop-theme, loop-count,
    correlation, ipc-position, agency, communion, axis-crossing, sycophancy-risk,
    fanfaronade-score, cold-weaver-topics, recurring-minor-elements,
    trigger-description, recommended-h-delta, and recommended-phase.
    danger-level accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    recommended-h-delta accepts values from -0.5 to +0.5.

    recurring-minor-elements entries must include user-reaction, content, type,
    count, and importance. Valid type values are in-joke, object-callback,
    ritual, and theme. Valid user-reaction values are neutral, engaged,
    amused, and callback.
    Valid recommended-phase values are null, probing, silent, reflection, and sparring.
    """

    _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_accepts_camel_case_contract_tokens():
    content = """
    Produce an object with intention, intentionLabel, intentionConfidence,
    defensivenessScore, defensivenessMarkers,
    dangerLevel, dangerSignals, themesLatents, loopDetected, loopTheme,
    loopCount, correlation, ipcPosition, agency, communion, axisCrossing, sycophancyRisk,
    fanfaronadeScore, coldWeaverTopics, recurringMinorElements,
    triggerDescription, recommendedHDelta, and recommendedPhase.
    dangerLevel accepts 0, 1, 2, and 3.
    correlation accepts null or an object with hypothesis and confidence.
    recommendedHDelta accepts values from -0.5 to +0.5.

    Each recurringMinorElements entry must include content, type, count, importance,
    and userReaction. Valid type values are inJoke, objectCallback, ritual,
    and theme. Valid userReaction values are neutral, engaged, amused,
    and callback.
    Valid recommendedPhase values are null, probing, silent, reflection, and sparring.
    """

    _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_recurring_entry_fields_only_before_anchor():
    content = """
    Glossary:
    content, type, count, importance, user_reaction.

    Output fields:
    intention, defensiveness_score, defensiveness_markers, danger_level,
    danger_signals, themes_latents, loop_detected, loop_theme, loop_count,
    correlation, ipc_position, axis_crossing, sycophancy_risk,
    fanfaronade_score, cold_weaver_topics, recommended_H_delta,
    recurring_minor_elements, trigger_description, recommended_phase.
    """

    with pytest.raises(ValueError, match="missing required contract token"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_validate_s2_prompt_rejects_missing_other_top_level_s2_schema_fields():
    content = _full_s2_contract_prompt(omit=("ipc_position",))

    with pytest.raises(ValueError, match="ipc_position"):
        _validate_prompt_content(S2_SYSTEM_PROMPT_PATH, content)


def test_get_s2_prompt_validates_runtime_content(monkeypatch):
    monkeypatch.setattr(
        "src.config._read_prompt",
        lambda _path: '{"danger_level": 0, "recommended_H_delta": 0.0}',
    )

    with pytest.raises(ValueError, match="missing required contract token"):
        get_s2_prompt()


def test_get_s2_prompt_caches_validated_content(monkeypatch):
    calls = []
    content = _full_s2_contract_prompt()

    def fake_read(_path):
        calls.append(True)
        return content

    monkeypatch.setattr("src.config._read_prompt", fake_read)

    assert get_s2_prompt() == content
    assert get_s2_prompt() == content
    assert len(calls) == 1


def test_validate_prompt_files_revalidates_cached_s2_prompt(monkeypatch):
    valid_content = _full_s2_contract_prompt()
    invalid_content = '{"danger_level": 0, "recommended_H_delta": 0.0}'
    stage = {"mode": "warm"}

    def fake_read(path):
        if path == S2_SYSTEM_PROMPT_PATH:
            return valid_content if stage["mode"] == "warm" else invalid_content
        return "non-empty prompt"

    monkeypatch.setattr("src.config._read_prompt", fake_read)

    assert get_s2_prompt() == valid_content

    stage["mode"] = "invalidate"

    with pytest.raises(ValueError, match="missing required contract token"):
        validate_prompt_files()
