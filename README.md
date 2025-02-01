# MeshCom-Client
A MeshCom-Client, written in Python, for using with MeshCom (https://icssw.org/meshcom/) Nodes

![image](https://github.com/user-attachments/assets/60b6d916-7173-42fe-9ea1-8844415e176a)

## What is this about?
This is a MeshCom-Client, that is written in Python for simple usage on a compatible computer system. Initially it is with very basic functionality but I think it will grow up over the next weeks :-)

## How to start
* Install python3 and fullfill requirements by installing all missing libraries.
* Connect your MeshCom-Node to your serial terminal and issue the following commands, to start the node to transfer data via udp to your computer:
  - --extudpip [ip of your computer]
  - --extudp on
* Go to Settings and put in the new destination ip address = ip of your node.

Now it should be running!

## Key features

* Grouping messages into tabs by destination (GRC or callsign)
* Alerting sound for new message
* Watchlist and alerting sound for callsigns in watchlist
* Restoring of chat-history on reopening chat-tabs
* Reopen specific chat on demand
* Delete complete chat history (also from restoring-source)

## Troubles?

If you have issues with emojis under linux, you could try `sudo apt-get install fonts-noto*` to install needed fonts

## ToDos

* View counter of new messages in tab
* Integration in "flutter"(Android and iOS-compatibility)

## Contributions
Sound Effect by <a href="https://pixabay.com/de/users/freesound_community-46691455/?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=40821">freesound_community</a> from <a href="https://pixabay.com/sound-effects//?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=40821">Pixabay</a>

Sound Effect by <a href="https://pixabay.com/de/users/rescopicsound-45188866/?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=230478">Rescopic Sound</a> from <a href="https://pixabay.com/sound-effects//?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=230478">Pixabay</a>
