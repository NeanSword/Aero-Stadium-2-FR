"""Apply PAL timing and VI scaling to the project's pinned native runtime."""
from pathlib import Path
import argparse


def patch(runtime):
    path = runtime / "ultramodern/src/events.cpp"
    text = path.read_text(encoding="utf-8-sig")
    if "// AERO_NP3F_VIDEO_V1" in text:
        print("NP3F video adapter already installed.")
        return

    def replace(old, new, count=1):
        nonlocal text
        if text.count(old) != count:
            raise SystemExit(f"Unexpected runtime source near {old!r}; no file changed")
        text = text.replace(old, new)

    replace("struct ViState {", """// AERO_NP3F_VIDEO_V1
// This runtime build is dedicated to the French PAL cartridge.
constexpr uint32_t aero_vi_hz = 50;
static uint32_t aero_scale_vi(uint32_t original, float factor) {
    return (original & ~0xFFFu) | (uint32_t(float(original & 0xFFFu) * factor) & 0xFFFu);
}

struct ViState {""")
    replace("    int retrace_count = 1;", "    int retrace_count = 1;\n    float x_factor = 1.0f;\n    float y_factor = 1.0f;")
    replace("uint32_t yScale = field_regs->yScale;", "uint32_t yScale = aero_scale_vi(field_regs->yScale, next_state->y_factor);")
    replace("regs.VI_X_SCALE_REG = common_regs->xScale; // TODO implement osViSetXScale", "regs.VI_X_SCALE_REG = aero_scale_vi(common_regs->xScale, next_state->x_factor);")
    replace("regs.VI_Y_SCALE_REG = yScale; // TODO implement osViSetYScale", "regs.VI_Y_SCALE_REG = yScale;")
    replace("(60 * ultramodern::get_speed_multiplier())", "(aero_vi_hz * ultramodern::get_speed_multiplier())", 2)
    for axis in ("X", "Y"):
        replace(f'''extern "C" void osViSet{axis}Scale(float scale) {{
    if (scale != 1.0f) {{
        assert(false);
    }}
}}''', f'''extern "C" void osViSet{axis}Scale(float scale) {{
    std::lock_guard lock{{ events_context.message_mutex }};
    events_context.vi.get_next_state()->{axis.lower()}_factor = scale;
}}''')
    replace("    next_state->mode = mode;", "    next_state->mode = mode;\n    next_state->x_factor = next_state->y_factor = 1.0f;")
    replace("        events_context.vi.update_vi();", "        {\n            std::lock_guard lock{ events_context.message_mutex };\n            events_context.vi.update_vi();\n        }")
    path.write_text(text, encoding="utf-8", newline="\n")
    print("Installed NP3F PAL 50 Hz and VI scaling adapter.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    patch(parser.parse_args().runtime)
