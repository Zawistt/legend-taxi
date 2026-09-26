extends RefCounted
## Klavishlarni InputMap'ga qo'shadi. Loyiha sozlamalarida qo'lda to'ldirish shart emas;
## Project Settings > Input Map'da xohlagancha o'zgartirishingiz mumkin (u yerdagilar ustun turadi).

const BINDINGS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"jump": [KEY_SPACE],
	"sprint": [KEY_SHIFT],
	"interact": [KEY_E],
	"drop_bomb": [KEY_G],
	"buy_menu": [KEY_B],
	"debug_zones": [KEY_F1],
	"debug_switch_team": [KEY_F2],
	"debug_restart_round": [KEY_F3],
}


static func ensure() -> void:
	for action in BINDINGS:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in BINDINGS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
