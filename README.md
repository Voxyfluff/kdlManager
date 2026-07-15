# kdlManager
## a Kdenlive project manager.

A linux-native, lightweight project manager for [Kdenlive](https://kdenlive.org/). kdlManager helps you organize and manage your Kdenlive projects from a graphical interface inspired by DaVinci Resolve's Project Library.

**Why?** Because I really like the Project Library of Resolve, and I love having a nice overview over all my projects. Also, I don't want to spend the $200+ for DaVinci Resolve Studio to edit like 2 videos a year, so I use Kdenlive instead.

## Features
- Overview of all `.kdenlive` projects added manually or via automatic folder searching
- Rename projects, add tags and notes
- Uses automatic thumbnails, but also supports custom project thumbnails (auto-thumbnails can be disabled via Experimental Settings)
- Handles `.kdenlive` files in a way where it is impossible to corrupt them (unless you use the Delete functionality, obviously)
- Uses `.kdlm` tarballs to store metadata like tags and the thumbnail

## Notes:
Keep in mind that this is my first time properly working with Qt, so things may look off.

**This project is still in Beta!** It's not far from finished, but there's still some stuff to add and improvements to be made. If you have suggestions, consider opening an [issue](https://github.com/Voxyfluff/kdlManager/issues).

Currently, only the native version of Kdenlive is supported. Flatpak and AppImage are not yet supported.

---

## License & Disclaimers

### License
kdlManager is licensed under the **GNU General Public License v3.0 (GPLv3)**, which is the same license used by Kdenlive and PyQt6. 
- See the [LICENSE](https://github.com/Voxyfluff/kdlManager/blob/main/LICENSE) file for the full text.
- You are welcome to use [kdlmUtils.py](https://github.com/Voxyfluff/kdlManager/blob/main/kdlmUtils.py) in your own projects under the same GPLv3 terms.

### Trademark Disclaimer
[Kdenlive](https://invent.kde.org/multimedia/kdenlive) is a registered trademark of the KDE Community. **kdlManager** is an independent, unofficial, open-source community project. It is not endorsed by, affiliated with, or maintained by the Kdenlive developers or the KDE project. They likely do not even know this project exists.

### Warranty & Liability (No Warranty)
This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**.
- **Use at your own risk.** This program interacts with your filesystem and includes file deletion capabilities. I (Voxyfluff) am not responsible for any accidental loss of data, or similar issues.
  
## Technical Requirements & Dependencies
- **Python & UI:** Written in Python 3.14.6 and uses PyQt6 6.11.
- **Multimedia Engine:** Requires `ffmpeg` or `ffmpeg-free` for automatic thumbnail generation. This feature can be turned off in the *Experimental Settings*.
- **Compatibility:** The pre-compiled executable is built against `glibc 2.31`. If your Linux distribution uses an older version, the compiled binary may not run correctly, and you should run the app from source instead. Run `ldd --version` in your terminal to find out which version your system uses.

---

## UI showcase
Main UI:

<img width="645" height="417" alt="image" src="https://github.com/user-attachments/assets/4c6b45ed-aefd-45b0-8776-769e601abfed" />

Editing project:

<img width="481" height="540" alt="image" src="https://github.com/user-attachments/assets/a2147e9c-66c7-443c-9387-6cfa6efe1be1" />
<img width="408" height="395" alt="image" src="https://github.com/user-attachments/assets/73bdca25-8acd-40f7-bb3d-c6563a6389bf" />

Settings Menu:

<img width="670" height="542" alt="image" src="https://github.com/user-attachments/assets/0d5e029a-cf36-4d45-9e49-9a87df299cbf" />

Experimental Settings: 

<img width="653" height="530" alt="image" src="https://github.com/user-attachments/assets/cf0281da-9a01-4361-9113-4b0ae56b0212" />

---

## kdlmUtils
You are welcome to use [kdlmUtils.py](https://github.com/Voxyfluff/kdlManager/blob/main/kdlmUtils.py) in your own projects if you need to parse `.kdenlive` files or handle `.kdlm` archives.

### `getKdlMeta(kdlProjectPath)`
Parses a `.kdenlive` project file (XML) to extract metadata properties.
- **Returns:** `tuple` -> `(projectID, duration, projectName, kdenliveVersion, docVersion)`

`kdenliveVersion` being the version of Kdenlive the project was last saved with, and `docVersion` being the version of the `.kdenlive` XML file.

### `scanIndexedFolders(folderPaths)`
Crawls provided directories to discover all `.kdenlive` projects. This is due for a rework to be more efficient and faster
- **Returns:** `foundFiles[]`, a list of absolute file paths.

### `readKdlmArchive(kdlmPath)`
Reads a `.kdlm` tarball and extracts `metadata.json` and the thumbnail.
- **Returns:** `(metadataDict, thumbnailBytes)` or `(None, None)` if missing/corrupt.

Layout of the metadata.json in the .kdlm file:

  <img width="379" height="209" alt="image" src="https://github.com/user-attachments/assets/c11afbaa-3f8f-4c60-827f-12e1409fde5c" />

`projectName` being the set display name, **not** the name of the `.kdenlive` file.

### `writeKdlmArchive(kdlmPath, metadataDict, thumbnailBytes)`
Creates or overwrites a `.kdlm` tarball with a metadata dictionary and optional thumbnail.

### `extractVideoFrame(kdenliveXmlPath)`
Parses the `.kdenlive` XML to find the first valid video clip resource inside a `<chain>`, resolves its path relative to the project directory, and extracts the second frame using `ffmpeg` (falls back to `ffmpeg-free`).
- **Returns:** Raw image bytes (PNG) or `None` if unsuccessful.




