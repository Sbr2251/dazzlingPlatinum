#include "battle/battle_events.h"

#include <nitro.h>

#include "constants/battle.h"
#include "constants/heap.h"

#include "battle/ability_popup.h"
#include "battle/ov16_0223DF00.h"

#include "heap.h"
#include "sys_task.h"
#include "sys_task_manager.h"

BattleEventsDebug gBattleEventsDebug = {
    .magic = BATTLE_EVENTS_DEBUG_MAGIC,
};

// ---------------------------------------------------------------------------------------------------------------

void BattleEvents_Shutdown(void)
{
    AbilityPopup_Shutdown();
}
