#include "battle/battle_bdsp_dialogue.h"

#include <nitro.h>
#include <string.h>

#include "constants/charcode.h"
#include "constants/graphics.h"

#include "battle/battle_bdsp_overlay.h"
#include "battle/battle_hud.h"
#include "port/hirestext.h"
#include "port/sim_battle3d.h"

#include "bg_window.h"
#include "charcode.h"
#include "system.h"
#include "text.h"

#define BDSP_DLG_MAX_PAGES 8
#define BDSP_DLG_MAX_TEXT  320
#define BDSP_DLG_MAX_SCAN  512

typedef struct BdspDialoguePage {
    char text[BDSP_DLG_MAX_TEXT];
    u16 charByteEnd[BDSP_DLG_MAX_TEXT];
    u16 charPause[BDSP_DLG_MAX_TEXT];
    u8 isInstantChar[BDSP_DLG_MAX_TEXT];
    u16 textLen;
    u16 numChars;
    u16 preRevealedChars;
    BOOL waitAtEnd;
    BOOL isScrollBreak;
} BdspDialoguePage;

typedef struct BdspDialogueState {
    BOOL hasMessage;
    BOOL suppressedBg1;
    BOOL printerActive;
    u8 printerId;
    int textSpeedBottom;
    int delayCounter;
    int pauseCounter;
    BOOL pauseConsumedForChar;
    int scrollDelay;
    int autoScrollDelay;
    BOOL speedUp;
    BOOL waitingForConfirm;
    int numPages;
    int pageIdx;
    int revealedChars;
    float alpha;
    BdspDialoguePage pages[BDSP_DLG_MAX_PAGES];
} BdspDialogueState;

static BdspDialogueState sDlg;

BOOL BattleBdspDialogue_IsActive(void)
{
#ifdef SDK_PORT
    return (SIM_Battle3D_ModelsEnabled() && BattleHud_IsHdMode()) ? TRUE : FALSE;
#else
    return FALSE;
#endif
}

static void SuppressBg1Layer(BattleSystem *battleSys)
{
    Bg_ToggleLayer(BG_LAYER_MAIN_1, FALSE);
    sDlg.suppressedBg1 = TRUE;

    if (battleSys != NULL) {
        BgConfig *bgConfig = BattleSystem_GetBgConfig(battleSys);
        if (bgConfig != NULL) {
            Bg_ClearTilemap(bgConfig, BG_LAYER_MAIN_1);
            Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
        }
    }

#ifdef SDK_PORT
    if (HiResText_IsEnabled()) {
        HiResText_ClearRect(0, 0, 0, 256, 192);
    }
#endif
}

static BOOL PageAppendUtf8(BdspDialoguePage *pg, const char *bytes, int nBytes, u16 pauseFrames, BOOL instant)
{
    int i;
    if (pg == NULL || nBytes <= 0) {
        return FALSE;
    }
    if (pg->textLen + nBytes >= BDSP_DLG_MAX_TEXT || pg->numChars >= BDSP_DLG_MAX_TEXT) {
        return FALSE;
    }
    for (i = 0; i < nBytes; i++) {
        pg->text[pg->textLen++] = bytes[i];
    }
    pg->text[pg->textLen] = '\0';
    pg->charByteEnd[pg->numChars] = pg->textLen;
    pg->charPause[pg->numChars] = pauseFrames;
    pg->isInstantChar[pg->numChars] = instant ? 1 : 0;
    pg->numChars++;
    return TRUE;
}

static int DecodePlatinumChar(charcode_t c, char out[4])
{
    if (c >= CHAR_0 && c <= CHAR_9) {
        out[0] = (char)('0' + (c - CHAR_0));
        return 1;
    }
    if (c >= CHAR_A && c <= CHAR_Z) {
        out[0] = (char)('A' + (c - CHAR_A));
        return 1;
    }
    if (c >= CHAR_a && c <= CHAR_z) {
        out[0] = (char)('a' + (c - CHAR_a));
        return 1;
    }
    if (c >= CHAR_WIDE_0 && c <= CHAR_WIDE_9) {
        out[0] = (char)('0' + (c - CHAR_WIDE_0));
        return 1;
    }
    if (c >= CHAR_WIDE_A && c <= CHAR_WIDE_Z) {
        out[0] = (char)('A' + (c - CHAR_WIDE_A));
        return 1;
    }
    if (c >= CHAR_WIDE_a && c <= CHAR_WIDE_z) {
        out[0] = (char)('a' + (c - CHAR_WIDE_a));
        return 1;
    }
    if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE || c == CHAR_NUM_SPACE
        || (c >= CHAR_SPACE_1px && c <= CHAR_SPACE_16px)) {
        out[0] = ' ';
        return 1;
    }

    switch (c) {
    case CHAR_EXCLAMATION:
    case CHAR_WIDE_EXCLAMATION:
        out[0] = '!';
        return 1;
    case CHAR_QUESTION:
    case CHAR_WIDE_QUESTION:
        out[0] = '?';
        return 1;
    case CHAR_PERIOD:
    case CHAR_WIDE_PERIOD:
    case CHAR_JP_PERIOD:
        out[0] = '.';
        return 1;
    case CHAR_COMMA:
    case CHAR_WIDE_COMMA:
    case CHAR_JP_COMMA:
        out[0] = ',';
        return 1;
    case CHAR_SINGLE_QUOTE_OPEN:
    case CHAR_SINGLE_QUOTE_CLOSE:
    case CHAR_JP_SINGLE_QUOTE_OPEN:
    case CHAR_JP_SINGLE_QUOTE_CLOSE:
        out[0] = '\'';
        return 1;
    case CHAR_DOUBLE_QUOTE_OPEN:
    case CHAR_DOUBLE_QUOTE_CLOSE:
    case CHAR_DOUBLE_QUOTE_CLOSE_INVERTED:
    case CHAR_JP_DOUBLE_QUOTE_OPEN:
    case CHAR_JP_DOUBLE_QUOTE_CLOSE:
        out[0] = '"';
        return 1;
    case CHAR_MINUS:
    case CHAR_WIDE_MINUS:
        out[0] = '-';
        return 1;
    case CHAR_COLON:
    case CHAR_WIDE_COLON:
        out[0] = ':';
        return 1;
    case CHAR_SEMICOLON:
    case CHAR_WIDE_SEMICOLON:
        out[0] = ';';
        return 1;
    case CHAR_SLASH:
    case CHAR_WIDE_SLASH:
    case CHAR_DIVIDE:
    case CHAR_WIDE_DIVIDE:
        out[0] = '/';
        return 1;
    case CHAR_PAREN_OPEN:
    case CHAR_JP_PAREN_OPEN:
    case CHAR_DOUBLE_PAREN_OPEN:
        out[0] = '(';
        return 1;
    case CHAR_PAREN_CLOSE:
    case CHAR_JP_PAREN_CLOSE:
    case CHAR_DOUBLE_PAREN_CLOSE:
        out[0] = ')';
        return 1;
    case CHAR_PLUS:
    case CHAR_WIDE_PLUS:
        out[0] = '+';
        return 1;
    case CHAR_STAR:
    case CHAR_WIDE_STAR:
    case CHAR_ASTERISK:
        out[0] = '*';
        return 1;
    case CHAR_MULTIPLY:
    case CHAR_WIDE_MULTIPLY:
        out[0] = 'x';
        return 1;
    case CHAR_PERCENT:
    case CHAR_WIDE_PERCENT:
        out[0] = '%';
        return 1;
    case CHAR_AMPERSAND:
    case CHAR_WIDE_AMPERSAND:
        out[0] = '&';
        return 1;
    case CHAR_TILDE:
    case CHAR_WIDE_TILDE:
        out[0] = '~';
        return 1;
    case CHAR_HASH:
        out[0] = '#';
        return 1;
    case CHAR_EQUALS:
    case CHAR_WIDE_EQUALS:
        out[0] = '=';
        return 1;
    case CHAR_AT_SIGN:
    case CHAR_WIDE_AT_SIGN:
        out[0] = '@';
        return 1;
    case CHAR_UNDERSCORE:
    case CHAR_WIDE_UNDERSCORE:
        out[0] = '_';
        return 1;
    case CHAR_POKEDOLLARS:
    case CHAR_YEN:
        out[0] = '$';
        return 1;
    case CHAR_DOT:
    case CHAR_JP_DOT:
        out[0] = '.';
        return 1;
    case CHAR_ELLIPSIS:
    case CHAR_JP_ELLIPSIS:
        out[0] = '.';
        out[1] = '.';
        out[2] = '.';
        return 3;
    case CHAR_MALE:
    case CHAR_WIDE_MALE:
        out[0] = (char)0xE2;
        out[1] = (char)0x99;
        out[2] = (char)0x82;
        return 3;
    case CHAR_FEMALE:
    case CHAR_WIDE_FEMALE:
        out[0] = (char)0xE2;
        out[1] = (char)0x99;
        out[2] = (char)0x80;
        return 3;
    case CHAR_e_ACUTE:
    case CHAR_e_SUPERSCRIPT:
        out[0] = (char)0xC3;
        out[1] = (char)0xA9;
        return 2;
    case CHAR_E_ACUTE:
        out[0] = (char)0xC3;
        out[1] = (char)0x89;
        return 2;
    case CHAR_PK:
        out[0] = 'P';
        out[1] = 'K';
        return 2;
    case CHAR_MN:
        out[0] = 'M';
        out[1] = 'N';
        return 2;
    case CHAR_DEGREES:
        out[0] = (char)0xC2;
        out[1] = (char)0xB0;
        return 2;
    case CHAR_EXCLAMATION_INVERTED:
        out[0] = (char)0xC2;
        out[1] = (char)0xA1;
        return 2;
    case CHAR_QUESTION_INVERTED:
        out[0] = (char)0xC2;
        out[1] = (char)0xBF;
        return 2;
    case CHAR_n_TILDE:
        out[0] = (char)0xC3;
        out[1] = (char)0xB1;
        return 2;
    case CHAR_N_TILDE:
        out[0] = (char)0xC3;
        out[1] = (char)0x91;
        return 2;
    case CHAR_u_DIERESIS:
        out[0] = (char)0xC3;
        out[1] = (char)0xBC;
        return 2;
    case CHAR_a_ACUTE:
        out[0] = (char)0xC3;
        out[1] = (char)0xA1;
        return 2;
    case CHAR_i_ACUTE:
        out[0] = (char)0xC3;
        out[1] = (char)0xAD;
        return 2;
    case CHAR_o_ACUTE:
        out[0] = (char)0xC3;
        out[1] = (char)0xB3;
        return 2;
    case CHAR_u_ACUTE:
        out[0] = (char)0xC3;
        out[1] = (char)0xBA;
        return 2;
    default:
        return 0;
    }
}

static BOOL HasMorePrintableChars(const charcode_t *p, const charcode_t *end)
{
    while (p < end && *p != CHAR_EOS) {
        charcode_t c = *p;
        if (c == CHAR_FORMAT_ARG) {
            const charcode_t *next = CharCode_SkipFormatArg(p);
            if (next <= p) {
                break;
            }
            p = next;
            continue;
        }
        if (c == CHAR_PLACEHOLDER_BEGIN) {
            p += 2;
            continue;
        }
        if (c == CHAR_CONTROL_CLEAR || c == CHAR_CONTROL_SCROLL || c == CHAR_CR) {
            p++;
            continue;
        }
        if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE || c == CHAR_NUM_SPACE
            || (c >= CHAR_SPACE_1px && c <= CHAR_SPACE_16px)) {
            p++;
            continue;
        }
        return TRUE;
    }
    return FALSE;
}

static void TrimPageTail(BdspDialoguePage *pg)
{
    while (pg->numChars > pg->preRevealedChars && pg->textLen > 0) {
        char last = pg->text[pg->textLen - 1];
        if (last != ' ' && last != '\n') {
            break;
        }
        pg->numChars--;
        pg->textLen = (pg->numChars > 0) ? pg->charByteEnd[pg->numChars - 1] : 0;
        pg->text[pg->textLen] = '\0';
    }
}

static void SeedScrolledPage(const BdspDialoguePage *prev, BdspDialoguePage *next)
{
    const char *nl;
    const char *tail;
    char ch;

    memset(next, 0, sizeof(*next));
    if (prev == NULL || prev->textLen == 0) {
        return;
    }
    nl = strrchr(prev->text, '\n');
    if (nl == NULL || nl[1] == '\0') {
        return;
    }

    // Carry the previous bottom line up to line 1 (matching Platinum's 2-line scroll).
    tail = nl + 1;
    while (*tail != '\0') {
        ch = *tail++;
        PageAppendUtf8(next, &ch, 1, 0, TRUE);
    }
    ch = '\n';
    PageAppendUtf8(next, &ch, 1, 0, TRUE);
    next->preRevealedChars = next->numChars;
}

static int ParseMessagePages(const String *msg, BdspDialoguePage outPages[BDSP_DLG_MAX_PAGES])
{
    const charcode_t *data;
    const charcode_t *p;
    const charcode_t *end;
    int pageCount = 1;
    u16 pendingPause = 0;

    memset(outPages, 0, sizeof(BdspDialoguePage) * BDSP_DLG_MAX_PAGES);
    if (msg == NULL) {
        return 0;
    }
    data = String_GetData(msg);
    if (data == NULL) {
        return 0;
    }

    p = data;
    end = data + BDSP_DLG_MAX_SCAN;

    while (p < end && *p != CHAR_EOS) {
        BdspDialoguePage *pg = &outPages[pageCount - 1];
        charcode_t c = *p;

        if (c == CHAR_PLACEHOLDER_BEGIN) {
            p += 2;
            continue;
        }

        if (c == CHAR_FORMAT_ARG) {
            u32 argType = CharCode_FormatArgType(p);
            const charcode_t *next = CharCode_SkipFormatArg(p);
            if (argType == CHAR_CONTROL_PAUSE) {
                pendingPause = (u16)(pendingPause + CharCode_FormatArgParam(p, 0));
            } else if (argType == CHAR_CONTROL_MOVE) {
                u16 param = (u16)CharCode_FormatArgParam(p, 0);
                if (param == 0xFE01 || param == 0xFE00) {
                    BOOL isScroll = (param == 0xFE00) ? TRUE : FALSE;
                    pg->waitAtEnd = TRUE;
                    pg->isScrollBreak = isScroll;
                    TrimPageTail(pg);
                    if (next > p && HasMorePrintableChars(next, end) && pageCount < BDSP_DLG_MAX_PAGES) {
                        if (isScroll) {
                            SeedScrolledPage(pg, &outPages[pageCount]);
                        }
                        pageCount++;
                    }
                    pendingPause = 0;
                }
            }
            if (next <= p) {
                break;
            }
            p = next;
            continue;
        }

        p++;

        if (c == CHAR_CR) {
            // Avoid leading newline or double blank line.
            if (pg->textLen > 0 && pg->text[pg->textLen - 1] != '\n') {
                char nl = '\n';
                PageAppendUtf8(pg, &nl, 1, pendingPause, TRUE);
                pendingPause = 0;
            }
            continue;
        }

        if (c == CHAR_CONTROL_CLEAR || c == CHAR_CONTROL_SCROLL) {
            BOOL isScroll = (c == CHAR_CONTROL_SCROLL) ? TRUE : FALSE;
            pg->waitAtEnd = TRUE;
            pg->isScrollBreak = isScroll;
            TrimPageTail(pg);
            if (HasMorePrintableChars(p, end) && pageCount < BDSP_DLG_MAX_PAGES) {
                if (isScroll) {
                    SeedScrolledPage(pg, &outPages[pageCount]);
                }
                pageCount++;
            }
            pendingPause = 0;
            continue;
        }

        {
            char utf8[4];
            int n = DecodePlatinumChar(c, utf8);
            if (n > 0) {
                // Skip leading spaces at start of page or right after newline, and collapse consecutive spaces.
                if (n == 1 && utf8[0] == ' ') {
                    if (pg->textLen == 0 || pg->text[pg->textLen - 1] == ' ' || pg->text[pg->textLen - 1] == '\n') {
                        continue;
                    }
                }
                PageAppendUtf8(pg, utf8, n, pendingPause, FALSE);
                pendingPause = 0;
            }
        }
    }

    TrimPageTail(&outPages[pageCount - 1]);
    if (pageCount == 1 && outPages[0].textLen == 0) {
        return 0;
    }
    return pageCount;
}

static BOOL IsWindowBitmapCleared(const Window *win)
{
    const u8 *px;
    u32 totalBytes;
    u32 i;
    u8 fillVal;

    if (win == NULL || win->bgConfig == NULL || win->pixels == NULL) {
        return FALSE;
    }
    totalBytes = (u32)win->width * (u32)win->height * 32u;
    if (totalBytes == 0) {
        return FALSE;
    }
    px = (const u8 *)win->pixels;
    fillVal = px[0];
    if (fillVal != 0xFF && fillVal != 0x00) {
        return FALSE;
    }
    for (i = 1; i < totalBytes; i++) {
        if (px[i] != fillVal) {
            return FALSE;
        }
    }
    return TRUE;
}

void BattleBdspDialogue_Reset(void)
{
    memset(&sDlg, 0, sizeof(sDlg));
    sDlg.printerId = MAX_TEXT_PRINTERS;
}

void BattleBdspDialogue_OnMessagePrint(BattleSystem *battleSys, const String *msg, u8 printerId, int textSpeed)
{
    BdspDialoguePage parsed[BDSP_DLG_MAX_PAGES];
    int numPages;
    BOOL wasVisible;

    if (!BattleBdspDialogue_IsActive()) {
        return;
    }

    SuppressBg1Layer(battleSys);

    if (msg == NULL) {
        return;
    }

    numPages = ParseMessagePages(msg, parsed);
    if (numPages <= 0) {
        sDlg.hasMessage = FALSE;
        sDlg.printerActive = FALSE;
        return;
    }

    // "What will <POKEMON> do?" / "What will <PLAYER> do/throw?" is printed
    // instantaneously (textSpeed == 0) right before the Action/Move menu opens.
    // Suppress it cleanly so it never flashes ahead of the BDSP menu.
    if (textSpeed == TEXT_SPEED_INSTANT
        && strncmp(parsed[0].text, "What will ", 10) == 0) {
        sDlg.hasMessage = FALSE;
        sDlg.printerActive = FALSE;
        sDlg.alpha = 0.0f;
        return;
    }

    wasVisible = sDlg.hasMessage;
    memcpy(sDlg.pages, parsed, sizeof(sDlg.pages));
    sDlg.numPages = numPages;
    sDlg.pageIdx = 0;
    sDlg.hasMessage = TRUE;
    sDlg.printerId = printerId;
    sDlg.delayCounter = 0;
    sDlg.pauseCounter = 0;
    sDlg.pauseConsumedForChar = FALSE;
    sDlg.scrollDelay = 0;
    sDlg.autoScrollDelay = 0;
    sDlg.speedUp = FALSE;
    sDlg.waitingForConfirm = FALSE;
    sDlg.alpha = wasVisible ? 1.0f : 0.25f;

    if (textSpeed == TEXT_SPEED_INSTANT || textSpeed == TEXT_SPEED_NO_TRANSFER || printerId >= MAX_TEXT_PRINTERS) {
        sDlg.printerActive = FALSE;
        sDlg.pageIdx = numPages - 1;
        sDlg.revealedChars = sDlg.pages[sDlg.pageIdx].numChars;
        sDlg.textSpeedBottom = 0;
    } else {
        sDlg.printerActive = TRUE;
        sDlg.textSpeedBottom = (textSpeed > 0) ? (textSpeed - 1) : 0;
        sDlg.revealedChars = 0;
    }
}

void BattleBdspDialogue_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame)
{
    BOOL overlayOpen;
    BOOL isYesNoMenu;
    BOOL menuOpen;
    int i;

    if (frame == NULL) {
        return;
    }

    if (!BattleBdspDialogue_IsActive()) {
        if (sDlg.suppressedBg1) {
            Bg_ToggleLayer(BG_LAYER_MAIN_1, TRUE);
            sDlg.suppressedBg1 = FALSE;
        }
        return;
    }

    // Keep Platinum's old pixel-art BG_LAYER_MAIN_1 battle text box completely suppressed.
    SuppressBg1Layer(battleSys);

    // Hide cleanly when Bag/Party/Summary overlays are active.
    overlayOpen = BattleBdspOverlay_IsActive() || (frame->overlay.kind != SIM_HUDHD_OVERLAY_NONE);
    if (overlayOpen) {
        frame->dialogue.visible = 0;
        return;
    }

    // Action/Move/Target menus and Y info cards hide the dialogue bar so the
    // full 3D clearing breathes. Yes/No prompts keep the question visible above.
    isYesNoMenu = FALSE;
    if (frame->numButtons > 0) {
        isYesNoMenu = TRUE;
        for (i = 0; i < frame->numButtons; i++) {
            if (frame->buttons[i].style != SIM_HUDHD_BUTTON_YES
                && frame->buttons[i].style != SIM_HUDHD_BUTTON_NO) {
                isYesNoMenu = FALSE;
                break;
            }
        }
    }
    menuOpen = (frame->numMoves > 0)
        || (frame->numButtons > 0 && !isYesNoMenu)
        || (frame->infoCard.visible != 0);

    if (menuOpen) {
        sDlg.hasMessage = FALSE;
        sDlg.printerActive = FALSE;
        sDlg.waitingForConfirm = FALSE;
        sDlg.alpha = 0.0f;
        frame->dialogue.visible = 0;
        return;
    }

    if (!sDlg.hasMessage || sDlg.numPages <= 0) {
        frame->dialogue.visible = 0;
        return;
    }

    // Sync live typewriter progress with Platinum's TextPrinter task.
    if (sDlg.printerActive) {
        BOOL live = (sDlg.printerId < MAX_TEXT_PRINTERS && Text_IsPrinterActive(sDlg.printerId)) ? TRUE : FALSE;
        if (!live) {
            sDlg.printerActive = FALSE;
            sDlg.pageIdx = sDlg.numPages - 1;
            sDlg.revealedChars = sDlg.pages[sDlg.pageIdx].numChars;
            sDlg.waitingForConfirm = FALSE;
            sDlg.autoScrollDelay = 0;
        } else if (sDlg.scrollDelay > 0) {
            sDlg.scrollDelay--;
        } else if (sDlg.waitingForConfirm) {
            BOOL confirmed = (JOY_NEW(PAD_BUTTON_A | PAD_BUTTON_B) || gSystem.touchPressed) ? TRUE : FALSE;
            if (confirmed || sDlg.autoScrollDelay >= 100) {
                sDlg.waitingForConfirm = FALSE;
                sDlg.autoScrollDelay = 0;
                if (sDlg.pageIdx + 1 < sDlg.numPages) {
                    BOOL wasScroll = sDlg.pages[sDlg.pageIdx].isScrollBreak;
                    sDlg.pageIdx++;
                    sDlg.revealedChars = sDlg.pages[sDlg.pageIdx].preRevealedChars;
                    sDlg.delayCounter = 0;
                    sDlg.pauseCounter = 0;
                    sDlg.pauseConsumedForChar = FALSE;
                    if (wasScroll) {
                        sDlg.scrollDelay = 4;
                    }
                }
            } else {
                sDlg.autoScrollDelay++;
            }
        } else if (sDlg.pauseCounter > 0) {
            sDlg.pauseCounter--;
        } else {
            BdspDialoguePage *pg = &sDlg.pages[sDlg.pageIdx];
            if ((JOY_HELD(PAD_BUTTON_A | PAD_BUTTON_B) && sDlg.speedUp) || gSystem.touchHeld) {
                sDlg.delayCounter = 0;
            }
            if (sDlg.delayCounter > 0 && sDlg.textSpeedBottom > 0) {
                sDlg.delayCounter--;
                if (JOY_NEW(PAD_BUTTON_A | PAD_BUTTON_B) || gSystem.touchPressed) {
                    sDlg.speedUp = TRUE;
                    sDlg.delayCounter = 0;
                }
            } else {
                sDlg.delayCounter = sDlg.textSpeedBottom;
                if (sDlg.revealedChars < pg->numChars) {
                    if (pg->charPause[sDlg.revealedChars] > 0 && !sDlg.pauseConsumedForChar) {
                        sDlg.pauseCounter = pg->charPause[sDlg.revealedChars];
                        sDlg.pauseConsumedForChar = TRUE;
                    } else {
                        sDlg.revealedChars++;
                        sDlg.pauseConsumedForChar = FALSE;
                        while (sDlg.revealedChars < pg->numChars && pg->isInstantChar[sDlg.revealedChars - 1]) {
                            sDlg.revealedChars++;
                        }
                    }
                }
                if (sDlg.revealedChars >= pg->numChars && pg->waitAtEnd) {
                    sDlg.waitingForConfirm = TRUE;
                    sDlg.autoScrollDelay = 0;
                }
            }
        }
    } else if (battleSys != NULL) {
        // If Platinum explicitly cleared windows[0] (BtlIOCmd_ClearMessageBox / MegaCine),
        // hide the dialogue bar cleanly.
        if (IsWindowBitmapCleared(BattleSystem_GetWindow(battleSys, 0))) {
            sDlg.hasMessage = FALSE;
            sDlg.alpha = 0.0f;
            frame->dialogue.visible = 0;
            return;
        }
    }

    {
        const BdspDialoguePage *pg = &sDlg.pages[sDlg.pageIdx];
        u16 byteLen = (sDlg.revealedChars > 0)
            ? pg->charByteEnd[sDlg.revealedChars - 1]
            : 0;
        if (byteLen >= sizeof(frame->dialogue.text)) {
            byteLen = sizeof(frame->dialogue.text) - 1;
        }

        if (sDlg.alpha < 1.0f) {
            sDlg.alpha += 0.25f;
            if (sDlg.alpha > 1.0f) {
                sDlg.alpha = 1.0f;
            }
        }

        frame->dialogue.visible = 1;
        memcpy(frame->dialogue.text, pg->text, byteLen);
        frame->dialogue.text[byteLen] = '\0';
        frame->dialogue.waitArrow = (sDlg.printerActive && sDlg.waitingForConfirm) ? 1 : 0;
        frame->dialogue.alpha = sDlg.alpha;

        // Lift bottom-left player HP cards cleanly above the wide dialogue bar
        // (y=148..184) so HP drains remain readable with zero overlap.
        for (i = 0; i < SIM_HUDHD_MAX_CARDS; i++) {
            if (frame->cards[i].visible && frame->cards[i].isPlayer
                && frame->cards[i].rect.y + frame->cards[i].rect.h > 142.0f) {
                frame->cards[i].rect.y -= 38.0f;
            }
        }
        frame->partyStrips[0].visible = 0;
    }
}
