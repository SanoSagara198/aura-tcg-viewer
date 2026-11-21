--!strict
-- AURA! TCG — complete card catalog, indexed by stable card ID.
-- Total: 1,115 records = 1,050 original cards + 65 basic-land entries.
-- Place this ModuleScript and the four sibling card modules under the same parent.
-- Records are frozen after adding a description alias for rules_text.
-- Server owns gameplay truth. Clients may read catalog definitions for display only.

local Cards: {[string]: any} = {}
local packs = {
    require(script.Parent.AlphaCards),
    require(script.Parent.BetaCards),
    require(script.Parent.DeltaCards),
    require(script.Parent.BasicLands),
}

for _, pack in ipairs(packs) do
    for id, card in pairs(pack) do
        assert(Cards[id] == nil, "Duplicate AURA card ID: " .. id)
        card.description = card.rules_text
        table.freeze(card)
        Cards[id] = card
    end
end

return table.freeze(Cards)
