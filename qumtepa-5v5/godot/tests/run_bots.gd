extends SceneTree
## 5v5 bot o'yinlari: balans sinovi. Ishga tushirish (godot/ papkasida):
##   godot --headless --fixed-fps 60 -s res://tests/run_bots.gd -- [raundlar soni] [seed]
## Natija: docs/bots_stage3.json (har bir raund + umumiy statistika) va qisqa hisobot.

var match_node: Node


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var n := int(args[0]) if args.size() > 0 else 180
	var sd := int(args[1]) if args.size() > 1 else 12345
	var scene: Node = load("res://bots.tscn").instantiate()
	match_node = scene.get_node("BotMatch")
	match_node.rounds_to_play = n
	match_node.seed_value = sd
	match_node.visual = false
	scene.get_node("Spectator").queue_free()
	root.add_child(scene)
	var t0 := Time.get_ticks_msec()
	var done := [false]
	var summary := {}
	match_node.all_done.connect(func(s): summary.merge(s); done[0] = true)
	match_node.round_finished.connect(func(st):
		if st.round % 20 == 0:
			print("  raund %d / %d (%.0f s)" % [st.round, n, (Time.get_ticks_msec() - t0) / 1000.0]))
	while not done[0]:
		await physics_frame
	print("\n5v5 BOT O'YINLARI: %d raund, seed %d, %.0f s" % [n, sd, (Time.get_ticks_msec() - t0) / 1000.0])
	print("  T yutdi: %.1f%%   bomba o'rnatildi: %.1f%%   o'rnatilgandan keyin CT qaytarib oldi: %.1f%%   birinchi o'lim: %.1f s" % [
		summary.t_win_pct, summary.plant_pct, summary.retake_pct, summary.avg_first_kill_s])
	print("\n  Site bo'yicha (T taktikasi qaysi site'ga):")
	for k in summary.by_site:
		var v = summary.by_site[k]
		print("    %-4s %3d raund, T %5.1f%%, o'rnatildi %d" % [k, v.rounds, v.t_win_pct, v.plants])
	print("\n  T taktikasi bo'yicha:")
	for k in summary.by_strategy:
		var v = summary.by_strategy[k]
		print("    %-34s %3d raund, T %5.1f%%, o'rnatildi %d" % [k, v.rounds, v.t_win_pct, v.plants])
	print("\n  CT joylashuvi bo'yicha:")
	for k in summary.by_setup:
		var v = summary.by_setup[k]
		print("    %-22s %3d raund, T %5.1f%%" % [k, v.rounds, v.t_win_pct])
	print("\n  Raund qanday tugadi:")
	for k in summary.reasons:
		print("    %-28s %d" % [k, summary.reasons[k]])
	var kw: Dictionary = summary.kills_by_callout
	var keys := kw.keys()
	keys.sort_custom(func(a, b): return kw[a] > kw[b])
	print("\n  Eng ko'p o'lim bo'lgan joylar:")
	for k in keys.slice(0, 10):
		print("    %-22s %d" % [k, kw[k]])
	var fw: Dictionary = summary.first_kills
	var fk := fw.keys()
	fk.sort_custom(func(a, b): return fw[a] > fw[b])
	print("\n  Birinchi o'lim (qayerdan → qayerga):")
	for k in fk.slice(0, 8):
		print("    %-48s %d" % [k, fw[k]])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://../docs/bots_stage3.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify({"summary": summary, "rounds": match_node.results, "seed": sd}, " "))
	f.close()
	quit()
