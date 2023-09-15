# battleshell
Battleship GUI game based off of my old Battleship Python shell game of the same name.
Battleshell contains a full game GUI with adjustable, persistent settings. It also contains
a work in progress local multiplayer mode and an adjustable AI for solo play.

# information
battleshell works in 3 parts:
  - A main Kivy application that houses the GUI, multiplayer connections and persistent board settings.
  - A battleshell class that functions as a fully working battleship game with adjustable settings.
  - A WaveWatch class that is a fully functional AI that can mimic a human opponent at highest settings.

While the Kivy GUI is not standalone as it is built around the battleshell class interface, the AI
and battleshell class are both standalone programs. Documentation is needed for how to properly use
these, but will be added eventually. Due to this encapsulation, you can create your own AI version to
replace WaveWatch and it should plug in directly. Similarly, if you need an AI for your own battleship
game, WaveWatch will also work, provided you know how to use it!

# images
<img width="875" alt="bshell_game" src="https://github.com/pbwz/battleshell/assets/116537322/463fe4d9-88e7-40e7-bb78-70bd8f48a98f">\
<img width="878" alt="bshell_settings" src="https://github.com/pbwz/battleshell/assets/116537322/f207773d-6f5f-4ff1-bd4b-776bb641ad66">

# final notes
This is the final evolution of my first major project so I apologize for any bugs or bad coding practices.
I've since improved and will likely come back to correct any mistakes and add some documentation!
