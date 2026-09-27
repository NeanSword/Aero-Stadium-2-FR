#ifndef AERO_PLATFORM_H
#define AERO_PLATFORM_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int32_t aero_cartridge_read_u32(uint32_t address);
void aero_map_fragment(uint32_t slot, int32_t ram, uint32_t size);
void aero_unmap_fragment(uint32_t slot);
void aero_poll_events(uint8_t* rdram);
#ifdef __cplusplus
}
#endif
#endif
