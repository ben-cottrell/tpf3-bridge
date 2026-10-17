function data()
 local react=ug_require "::/gui/main/react.lua"
 local builtin=ug_require "::/gui/main/builtin.lua"
 local area=ug_require "::/gui/main/main_mod_button_area.tl"
 return {NCDC13Button=react.RegisterPluginRecipe(area.MainModButtonAreaExtension,"NCDC13Button",function()
  return builtin.BoxLayout{children={builtin.TextView{text="P01 Live Python Adapter"}}}
 end)}
end
