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
#include "text.h"

#define BDSP_DLG_MAX_PAGES 8
#define BDSP_DLG_MAX_TEXT  320
#define BDSP_DLG_MAX_SCAN  512

typedef struct BdspDialoguePage {
    char text[BDSP_DLG_MAX_TEXT];
    u16 charByteEnd[BDSP_DLG_MAX_TEXT];
    u16 charSrcEnd[BDSP_DLG_MAX_TEXT];
    u16 textLen;
    u16 numChars;
    u16 preRevealedChars;
    u16 breakSrcOffset;
    BOOL waitAtEnd;
    BOOL isScrollBreak;
} BdspDialoguePage;

typedef struct BdspDialogueState {
    BOOL hasMessage;
    BOOL suspended;
    BOOL fallbackToLegacy;
    BOOL printerActive;
    u8 printerId;
    const Window *activeMsgWindow;
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

BOOL BattleBdspDialogue_ShouldSuppressWindow(const Window *window)
{
    if (!BattleBdspDialogue_IsActive() || sDlg.suspended || sDlg.fallbackToLegacy) {
        return FALSE;
    }
    if (window == NULL || window->bgConfig == NULL || sDlg.activeMsgWindow == NULL) {
        return FALSE;
    }
    return (window == sDlg.activeMsgWindow) ? TRUE : FALSE;
}

// Suppress ONLY the battle message window's tile rect (plus its PL_WINFRAME
// border and scroll-cursor tiles) on BG_LAYER_MAIN_1. Never disables or wipes
// all of BG_LAYER_MAIN_1, so non-battle / Pokédex sub-apps sharing BgConfig
// retain full ownership of BG1.
static void SuppressBattleMsgWindowRect(BattleSystem *battleSys)
{
    Window *msgWin;
    BgConfig *bgConfig;
    int fx, fy, fw, fh;

    if (battleSys == NULL || sDlg.suspended || sDlg.fallbackToLegacy) {
        return;
    }

    msgWin = BattleSystem_GetWindow(battleSys, 0);
    if (msgWin == NULL || msgWin->bgConfig == NULL || msgWin->bgLayer != BG_LAYER_MAIN_1) {
        sDlg.activeMsgWindow = NULL;
        return;
    }

    sDlg.activeMsgWindow = msgWin;
    bgConfig = msgWin->bgConfig;

    fx = (msgWin->tilemapLeft >= 2) ? ((int)msgWin->tilemapLeft - 2) : 0;
    fy = (msgWin->tilemapTop >= 1) ? ((int)msgWin->tilemapTop - 1) : 0;
    fw = (int)msgWin->width + 5; // 2 left border + window + 3 right border/scroll arrow
    fh = (int)msgWin->height + 2; // 1 top border + window + 1 bottom border
    if (fx + fw > 43) {
        fw = 43 - fx;
    }
    if (fy + fh > 24) {
        fh = 24 - fy;
    }
    if (fw > 0 && fh > 0) {
        Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 0, (u8)fx, (u8)fy, (u8)fw, (u8)fh, 0);
        Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
    }

#ifdef SDK_PORT
    if (HiResText_IsEnabled()) {
        HiResText_ClearRect(0,
            (int)msgWin->tilemapLeft * 8,
            (int)msgWin->tilemapTop * 8,
            (int)msgWin->width * 8,
            (int)msgWin->height * 8);
    }
#endif
}

static BOOL PageAppendUtf8(BdspDialoguePage *pg, const char *bytes, int nBytes, u16 srcEnd)
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
    pg->charSrcEnd[pg->numChars] = srcEnd;
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

static BOOL HasMorePrintableChars(const charcode_t *data, u32 startIdx, u32 limit)
{
    u32 idx = startIdx;

    while (idx < limit && data[idx] != CHAR_EOS) {
        charcode_t c = data[idx];
        if (c == CHAR_FORMAT_ARG) {
            u32 argc;
            u32 recLen;
            if (idx + 3u > limit) {
                break;
            }
            argc = (u32)data[idx + 2u];
            recLen = 3u + argc;
            if (recLen > limit - idx) {
                break;
            }
            idx += recLen;
            continue;
        }
        if (c == CHAR_PLACEHOLDER_BEGIN) {
            if (idx + 2u > limit) {
                break;
            }
            idx += 2u;
            continue;
        }
        if (c == CHAR_CONTROL_CLEAR || c == CHAR_CONTROL_SCROLL || c == CHAR_CR) {
            idx++;
            continue;
        }
        if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE || c == CHAR_NUM_SPACE
            || (c >= CHAR_SPACE_1px && c <= CHAR_SPACE_16px)) {
            idx++;
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
        PageAppendUtf8(next, &ch, 1, 0);
    }
    ch = '\n';
    PageAppendUtf8(next, &ch, 1, 0);
    next->preRevealedChars = next->numChars;
}

static int ParseMessagePages(const String *msg, BdspDialoguePage outPages[BDSP_DLG_MAX_PAGES])
{
    const charcode_t *data;
    u32 msgLen;
    u32 limit;
    u32 idx = 0;
    int pageCount = 1;

    memset(outPages, 0, sizeof(BdspDialoguePage) * BDSP_DLG_MAX_PAGES);
    if (msg == NULL) {
        return 0;
    }
    data = String_GetData(msg);
    if (data == NULL) {
        return 0;
    }
    msgLen = String_Length(msg);
    limit = (msgLen < BDSP_DLG_MAX_SCAN) ? msgLen : BDSP_DLG_MAX_SCAN;

    while (idx < limit && data[idx] != CHAR_EOS) {
        BdspDialoguePage *pg = &outPages[pageCount - 1];
        charcode_t c = data[idx];

        if (c == CHAR_PLACEHOLDER_BEGIN) {
            if (idx + 2u > limit) {
                break;
            }
            idx += 2u;
            continue;
        }

        if (c == CHAR_FORMAT_ARG) {
            u16 argType;
            u32 argc;
            u32 recLen;
            if (idx + 3u > limit) {
                break;
            }
            argType = data[idx + 1u];
            argc = (u32)data[idx + 2u];
            recLen = 3u + argc;
            if (recLen > limit - idx) {
                break;
            }
            if (argType == CHAR_CONTROL_MOVE && argc >= 1u) {
                u16 param = data[idx + 3u];
                if (param == 0xFE01 || param == 0xFE00) {
                    BOOL isScroll = (param == 0xFE00) ? TRUE : FALSE;
                    u32 nextIdx = idx + recLen;
                    pg->waitAtEnd = TRUE;
                    pg->isScrollBreak = isScroll;
                    pg->breakSrcOffset = (u16)nextIdx;
                    TrimPageTail(pg);
                    if (HasMorePrintableChars(data, nextIdx, limit) && pageCount < BDSP_DLG_MAX_PAGES) {
                        if (isScroll) {
                            SeedScrolledPage(pg, &outPages[pageCount]);
                        }
                        pageCount++;
                    }
                }
            }
            idx += recLen;
            continue;
        }

        idx++;

        if (c == CHAR_CR) {
            if (pg->textLen > 0 && pg->text[pg->textLen - 1] != '\n') {
                char nl = '\n';
                PageAppendUtf8(pg, &nl, 1, (u16)idx);
            }
            continue;
        }

        if (c == CHAR_CONTROL_CLEAR || c == CHAR_CONTROL_SCROLL) {
            BOOL isScroll = (c == CHAR_CONTROL_SCROLL) ? TRUE : FALSE;
            pg->waitAtEnd = TRUE;
            pg->isScrollBreak = isScroll;
            pg->breakSrcOffset = (u16)idx;
            TrimPageTail(pg);
            if (HasMorePrintableChars(data, idx, limit) && pageCount < BDSP_DLG_MAX_PAGES) {
                if (isScroll) {
                    SeedScrolledPage(pg, &outPages[pageCount]);
                }
                pageCount++;
            }
            continue;
        }

        {
            char utf8[4];
            int n = DecodePlatinumChar(c, utf8);
            if (n > 0) {
                if (n == 1 && utf8[0] == ' ') {
                    if (pg->textLen == 0 || pg->text[pg->textLen - 1] == ' ' || pg->text[pg->textLen - 1] == '\n') {
                        continue;
                    }
                }
                PageAppendUtf8(pg, utf8, n, (u16)idx);
            }
        }
    }

    {
        BdspDialoguePage *lastPg = &outPages[pageCount - 1];
        TrimPageTail(lastPg);
        if (lastPg->breakSrcOffset == 0) {
            lastPg->breakSrcOffset = (u16)idx;
        }
    }

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

void BattleBdspDialogue_Suspend(void)
{
    sDlg.suspended = TRUE;
    sDlg.hasMessage = FALSE;
    sDlg.printerActive = FALSE;
    sDlg.fallbackToLegacy = FALSE;
    sDlg.activeMsgWindow = NULL;
    sDlg.alpha = 0.0f;
}

void BattleBdspDialogue_Resume(void)
{
    sDlg.suspended = FALSE;
    sDlg.hasMessage = FALSE;
    sDlg.printerActive = FALSE;
    sDlg.fallbackToLegacy = FALSE;
    sDlg.alpha = 0.0f;
}

void BattleBdspDialogue_OnMessagePrint(BattleSystem *battleSys, const String *msg, u8 printerId, int textSpeed)
{
    BdspDialoguePage parsed[BDSP_DLG_MAX_PAGES];
    Window *textWindow;
    int numPages;
    BOOL wasVisible;

    if (!BattleBdspDialogue_IsActive() || sDlg.suspended) {
        return;
    }

    textWindow = (battleSys != NULL) ? BattleSystem_GetWindow(battleSys, 0) : NULL;
    if (textWindow == NULL || textWindow->bgConfig == NULL) {
        sDlg.activeMsgWindow = NULL;
        return;
    }

    if (msg == NULL) {
        return;
    }

    numPages = ParseMessagePages(msg, parsed);
    if (numPages <= 0) {
        sDlg.hasMessage = FALSE;
        sDlg.printerActive = FALSE;
        if (String_Length(msg) > 0) {
            // Unparseable non-empty message: fall back cleanly to the legacy window.
            sDlg.fallbackToLegacy = TRUE;
            if (textSpeed == TEXT_SPEED_INSTANT) {
                Window_CopyToVRAM(textWindow);
            }
        }
        return;
    }

    sDlg.fallbackToLegacy = FALSE;
    sDlg.activeMsgWindow = textWindow;
    SuppressBattleMsgWindowRect(battleSys);

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
    sDlg.alpha = wasVisible ? 1.0f : 0.25f;

    if (textSpeed == TEXT_SPEED_INSTANT || textSpeed == TEXT_SPEED_NO_TRANSFER || printerId >= MAX_TEXT_PRINTERS) {
        sDlg.printerActive = FALSE;
        sDlg.pageIdx = numPages - 1;
        sDlg.revealedChars = sDlg.pages[sDlg.pageIdx].numChars;
    } else {
        sDlg.printerActive = TRUE;
        sDlg.revealedChars = 0;
    }
}

void BattleBdspDialogue_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame)
{
    Window *msgWin;
    BOOL overlayOpen;
    BOOL isYesNoMenu;
    BOOL menuOpen;
    int waitArrow = 0;
    int i;

    if (frame == NULL) {
        return;
    }

    if (!BattleBdspDialogue_IsActive() || sDlg.suspended) {
        frame->dialogue.visible = 0;
        return;
    }

    // Do not touch BG_LAYER_MAIN_1 if windows[0] is removed (e.g. Pokédex
    // registration screen or battle screen hidden).
    msgWin = (battleSys != NULL) ? BattleSystem_GetWindow(battleSys, 0) : NULL;
    if (msgWin == NULL || msgWin->bgConfig == NULL) {
        sDlg.activeMsgWindow = NULL;
        frame->dialogue.visible = 0;
        return;
    }

    if (sDlg.fallbackToLegacy) {
        frame->dialogue.visible = 0;
        return;
    }

    // Suppress ONLY the battle message window tile rect on BG_LAYER_MAIN_1.
    SuppressBattleMsgWindowRect(battleSys);

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
        sDlg.alpha = 0.0f;
        frame->dialogue.visible = 0;
        return;
    }

    if (!sDlg.hasMessage || sDlg.numPages <= 0) {
        frame->dialogue.visible = 0;
        return;
    }

    // Sync live page, character progress, and waitArrow directly from the real TextPrinter.
    if (sDlg.printerActive) {
        TextPrinterProgress prog;
        if (!Text_GetPrinterProgress(sDlg.printerId, &prog)) {
            sDlg.printerActive = FALSE;
            sDlg.pageIdx = sDlg.numPages - 1;
            sDlg.revealedChars = sDlg.pages[sDlg.pageIdx].numChars;
            waitArrow = 0;
        } else {
            int p = 0;
            while (p + 1 < sDlg.numPages) {
                u16 brk = sDlg.pages[p].breakSrcOffset;
                if (prog.charOffset < brk) {
                    break;
                }
                // Stay on page p while the real printer is still waiting on its
                // page break (WAIT/CLEAR/START_SCROLL) or mid-scroll (state 4).
                if (prog.charOffset == brk && (prog.waitingInput || prog.state == 4)) {
                    break;
                }
                p++;
            }
            sDlg.pageIdx = p;
            {
                const BdspDialoguePage *pg = &sDlg.pages[p];
                int r = (int)pg->preRevealedChars;
                while (r < (int)pg->numChars && pg->charSrcEnd[r] <= prog.charOffset) {
                    r++;
                }
                sDlg.revealedChars = r;
            }
            waitArrow = prog.waitingInput ? 1 : 0;
        }
    } else {
        // If Platinum explicitly cleared windows[0] (BtlIOCmd_ClearMessageBox / MegaCine),
        // hide the dialogue bar cleanly.
        if (IsWindowBitmapCleared(msgWin)) {
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
        frame->dialogue.waitArrow = waitArrow;
        frame->dialogue.alpha = sDlg.alpha;

        // Lift bottom-left player HP cards cleanly above the wide dialogue bar
        // (y=150..184) so HP drains remain readable with zero overlap.
        for (i = 0; i < SIM_HUDHD_MAX_CARDS; i++) {
            if (frame->cards[i].visible && frame->cards[i].isPlayer
                && frame->cards[i].rect.y + frame->cards[i].rect.h > 142.0f) {
                frame->cards[i].rect.y -= 38.0f;
            }
        }
        frame->partyStrips[0].visible = 0;
    }
}
