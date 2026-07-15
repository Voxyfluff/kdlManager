# kdlmUtils.py
import os
import xml.etree.ElementTree as ET
import tarfile
import io
import json
import subprocess


def getKdlMeta(kdlProjectPath):
    """
    Parses .kdenlive project file to extract metadata properties.

    Returns:
        tuple: (projectID, duration, projectName, kdenliveVersion, docVersion)
    """
    projectID = "projectID Not Found"
    duration = "Duration Not Found"
    projectName = "Filename Not Found"
    kdenliveVersion = "Version Not Found"
    docVersion = "DocVersion Not Found"

    if not os.path.exists(kdlProjectPath):
        return projectID, duration, projectName, kdenliveVersion, docVersion

    projectName = os.path.basename(kdlProjectPath).split('.', 1)[0]

    try:
        tree = ET.parse(kdlProjectPath)
        root = tree.getroot()
    except ET.ParseError:
        return projectID, duration, projectName, kdenliveVersion, docVersion

    main_bin = root.find(".//playlist[@id='main_bin']")
    if main_bin is not None:
        for prop in main_bin.findall('property'):
            prop_name = prop.get('name')
            if prop_name == 'kdenlive:docproperties.documentid':
                projectID = prop.text or "Not Found"
            elif prop_name == 'kdenlive:docproperties.kdenliveversion':
                kdenliveVersion = prop.text or "Not Found"
            elif prop_name == 'kdenlive:docproperties.version':
                docVersion = prop.text or "Not Found"

    for prop in root.findall('.//property'):
        if prop.get('name') == 'kdenlive:duration':
            val = prop.text
            if val and val != "00:00:00:00" and val != "00:00:00.000":
                duration = val
                break

    return projectID, duration, projectName, kdenliveVersion, docVersion



def scanIndexedFolders(folderPaths):
    """
    Crawls folder paths to discover all .kdenlive projects.
    Returns a list of unique absolute paths.
    """
    foundFiles = []
    for folder in folderPaths:
        if os.path.exists(folder) and os.path.isdir(folder):
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith(".kdenlive"):
                        fullPath = os.path.join(root, file)
                        if fullPath not in foundFiles:
                            foundFiles.append(fullPath)
    return foundFiles



def readKdlmArchive(kdlmPath):
    """
    Reads a .kdlm tarball and extracts metadata.json as a dictionary.
    Returns: (metadataDict, thumbnailBytes) or (None, None) if missing/corrupt.
    """
    if not os.path.exists(kdlmPath):
        return None, None

    metadataDict = None
    thumbnailBytes = None

    try:
        with tarfile.open(kdlmPath, "r") as tar:

            try:
                metadataMember = tar.getmember("metadata.json")
                f = tar.extractfile(metadataMember)
                if f:
                    metadataDict = json.loads(f.read().decode("utf-8"))
            except KeyError:
                pass

            try:
                thumbnailMember = tar.getmember("thumbnail.png")
                f = tar.extractfile(thumbnailMember)
                if f:
                    thumbnailBytes = f.read()
            except KeyError:
                pass

    except Exception as e:
        print(f"Error reading .kdlm archive: {e}")

    return metadataDict, thumbnailBytes

def writeKdlmArchive(kdlmPath, metadataDict, thumbnailBytes=None):
    """
    Creates or overwrites a .kdlm tarball with metadata and an optional thumbnail.
    """
    try:
        jsonBytes = json.dumps(metadataDict, indent=4).encode("utf-8")

        with tarfile.open(kdlmPath, "w") as tar:
            metaTarInfo = tarfile.TarInfo(name="metadata.json")
            metaTarInfo.size = len(jsonBytes)
            tar.addfile(metaTarInfo, io.BytesIO(jsonBytes))

            if thumbnailBytes:
                thumbTarInfo = tarfile.TarInfo(name="thumbnail.png")
                thumbTarInfo.size = len(thumbnailBytes)
                tar.addfile(thumbTarInfo, io.BytesIO(thumbnailBytes))

        return True
    except Exception as e:
        print(f"Error writing .kdlm archive: {e}")
        return False



def extractFrameBytes(binary_name, video_path):
    """
    Helper function to run the frame extraction command for a given binary name.
    """
    cmd = [
        binary_name,
        "-ss", "0",
        "-i", video_path,
        "-vf", "select=eq(n\\,1)",
        "-vframes", "1",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"
    ]

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo
    )
    stdout_bytes, _ = process.communicate(timeout=5)

    if process.returncode == 0 and stdout_bytes:
        return stdout_bytes
    return None

def extractVideoFrame(kdenliveXmlPath):
    """
    Parses the .kdenlive XML to find the first valid video clip resource inside a <chain>,
    resolves its path relative to the project directory, and extracts the second frame.
    Returns raw image bytes (PNG) or None if unsuccessful.
    """
    if not os.path.exists(kdenliveXmlPath):
        return None

    try:
        tree = ET.parse(kdenliveXmlPath)
        root = tree.getroot()
    except ET.ParseError:
        return None

    firstVideoPath = None
    project_dir = os.path.dirname(kdenliveXmlPath)

    for chain in root.findall(".//chain"):
        resource_prop = chain.find("./property[@name='resource']")
        if resource_prop is not None and resource_prop.text:
            resource_path = resource_prop.text.strip()

            if not os.path.isabs(resource_path):
                resolved = os.path.normpath(os.path.join(project_dir, resource_path))
            else:
                resolved = resource_path

            if os.path.exists(resolved) and os.path.isfile(resolved):
                lower_path = resolved.lower()
                if lower_path.endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.flv')):
                    firstVideoPath = resolved
                    break

    if not firstVideoPath:
        return None

    try:
        frame_bytes = extractFrameBytes("ffmpeg", firstVideoPath)
        if frame_bytes:
            return frame_bytes
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    # if ffmpeg is not installed try ffmpeg-free
    try:
        frame_bytes = extractFrameBytes("ffmpeg-free", firstVideoPath)
        if frame_bytes:
            return frame_bytes
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return None
