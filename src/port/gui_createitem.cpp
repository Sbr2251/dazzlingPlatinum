#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>

#include "sim_gui_prj.hpp"

#include "port/sim_config_prj.h"

#include "generated/items.h"
#include "gui_createitem_utils.h"


#include <string>
#include <vector>

namespace SIM::GUI {

static std::vector<std::string> sItemNames;
static int sItemNum = 0;
static int sQuantity = 1;

static constexpr ImVec2 BtnSize = {100, 20};

void CreateItemInit() {
    sItemNames.clear();
    sItemNames.push_back("None");

    for(int i=1; i <= MAX_ITEMS; i++) {
        const char * itemName = GUI_CreateItem_GetItemName(i);
        sItemNames.push_back(std::string(itemName));
        delete itemName;
    }
}

void CreateItemMain(bool * openState) {
    ImGui::Begin("Gen Items", openState);

    ImGui::Combo("Item", &sItemNum, [](void * vec, int idx){
        std::vector<std::string>* vector = reinterpret_cast<std::vector<std::string>*>(vec);
        if(idx < 0 || idx > vector->size()) {
            return "";
        }

        return vector->at(idx).c_str();
    }, reinterpret_cast<void*>(&sItemNames), sItemNames.size());

    ImGui::InputScalar("Quantity", ImGuiDataType_U8, &sQuantity, nullptr, nullptr, nullptr, ImGuiInputTextFlags_CharsDecimal);

    if(ImGui::Button("Gen Items", BtnSize)) {
        GUI_CreateItem_GenItems(sItemNum, sQuantity);
    }

    ImGui::End();
}
}