-- ForgeUI example: a two-tab options window in the AutoLazy layout.
-- Replace MyAddon / MyAddonDB with the addon's names. Not loaded by itself.
local addonName, ns = ...
local UI = ns.UI

local panel, ShowTab

local function Create()
    panel = UI.Window("MyAddon_Options", "MyAddon", 500, 300, GetAddOnMetadata(addonName, "Version"))

    local refresh = {}
    local pages
    pages, ShowTab = UI.Tabs(panel, "MyAddon_", {
        { label = "General", height = 300 },
        { label = "Display", height = 260 },
    }, function(index)
        MyAddonDB.SelectedTab = index
        refresh[index]()
    end)

    -- General: heading at -98, rows 36 apart, two columns at x = 28 and 264.
    -- Action buttons sit in the right column at x = 300, width 172.
    local general = pages[1]
    UI.Heading(general, "Behavior", 28, -98)
    local enabled, verbose
    enabled = UI.Switch("MyAddon_Enabled", general, "Enable MyAddon",
        "Turn the addon's automation on or off.", 28, -122, function(value)
            MyAddonDB.Enabled = value
            refresh[1]()
        end)
    UI.Button("MyAddon_Reset", general, "Reset position", 300, -120, 172, function() end)
    verbose = UI.Switch("MyAddon_Verbose", general, "Chat messages",
        "Print a line when MyAddon acts.", 44, -158, function(value)
            MyAddonDB.Verbose = value
        end)
    UI.Label(general, "Left-click: open   /   Drag: move", 28, -200, "GameFontDisableSmall")
    local footer = UI.Button("MyAddon_More", general, "More options", 0, 0, 172, function() end)
    footer:ClearAllPoints()
    footer:SetPoint("BOTTOMLEFT", general, "BOTTOMLEFT", 28, 18)
    refresh[1] = function()
        UI.Sync(enabled, MyAddonDB.Enabled)
        -- Dependent choices dim while their parent is off.
        UI.Sync(verbose, MyAddonDB.Verbose, MyAddonDB.Enabled)
    end

    -- Display: a radio choice per row.
    local display = pages[2]
    UI.Heading(display, "Size", 28, -98)
    local sizes, radios = { "Small", "Medium", "Large" }, {}
    for i = 1, 3 do
        local size = sizes[i]
        local row = UI.Row("MyAddon_SizeRow" .. i, display, 28, -122 - (i - 1) * 28, 200)
        local radio = UI.Radio("MyAddon_Size" .. i, row)
        radio:SetPoint("LEFT", row, "LEFT", 4, 0)
        radio:SetScript("OnClick", function()
            MyAddonDB.Size = size
            refresh[2]()
        end)
        local label = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        label:SetPoint("LEFT", radio, "RIGHT", 8, 0)
        label:SetText(size)
        UI.Color(label, "text")
        radios[i] = radio
    end
    refresh[2] = function()
        for i = 1, 3 do UI.SetCheck(radios[i], MyAddonDB.Size == sizes[i]) end
    end

    panel:SetScript("OnShow", function() ShowTab(MyAddonDB.SelectedTab or 1) end)
end

function MyAddon_ToggleOptions()
    if not panel then Create() end
    if panel:IsShown() then panel:Hide() else panel:Show() end
end
