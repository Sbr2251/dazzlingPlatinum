#include "battle/battle_bdsp_capture.h"

void BattleBdspCapture_Reset(void) {}
void BattleBdspCapture_Start(BattleSystem *battleSys, int targetBattler, int ballItemId, int shakes, BOOL caught) { (void)battleSys; (void)targetBattler; (void)ballItemId; (void)shakes; (void)caught; }
void BattleBdspCapture_End(void) {}
BOOL BattleBdspCapture_IsActive(void) { return FALSE; }
void BattleBdspCapture_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame) { (void)battleSys; (void)frame; }
