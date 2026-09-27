extends SceneTree
## Inventar ekrani skrinshotlari: 56_inventar_cs2.png, 57_inventar_zaxira.png, 58_inventar_pubg.png


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var inv: Control = load("res://scripts/inventory.gd").new()
	root.add_child(inv)
	for i in 3:
		inv.select_tab(i)
		var ws: Array = inv.weapons_of(inv.TABS[i][0])
		inv.show_weapon(ws[mini(2, ws.size() - 1)])
		for f in 12:
			await process_frame
		root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % ["56_inventar_cs2", "57_inventar_zaxira", "58_inventar_pubg"][i]))
		print("saqlandi ", i, " ", ws.size())
	quit()
