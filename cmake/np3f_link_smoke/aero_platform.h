#pragma once

// Compatibility shim for an older locally generated recomp_overlays.inl that
// referenced aero_platform.h. The current NP3F N64Recomp configuration uses
// recomp.h directly, but keeping this tiny bridge lets existing generated
// artifacts remain linkable until they are regenerated.
#include "recomp.h"
