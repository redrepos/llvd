from tqdm import tqdm
import requests
import click
import os
from llvd.utils import clean_name, subtitles_time_format, throttle


def download_video(url, index, filename, path, delay=None, proxies=None):
    """
    Download video file with progress bar and retry logic.
    
    Args:
        url (str): The URL of the video to download
        index (int): The index of the video in the course
        filename (str): The name to save the file as
        path (str): The directory to save the file in
        delay (tuple, optional): Min,max wait in seconds between chunks
        proxies (list, optional): List of proxy URLs to use for the download
    """
    if delay:
        throttle(delay)
        
    filename = clean_name(filename)
    filepath = os.path.join(path, f"{index:02d} {filename}.mp4")
    
    # Skip if file already exists and has content
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        click.echo(click.style(f"✓ {filename} already exists", fg="green"))
        return True
    
    # Create a session for connection pooling
    session = requests.Session()
    
    # Configure proxy if available
    if proxies and len(proxies) > 0:
        proxy = proxies[0] if isinstance(proxies, list) else proxies
        session.proxies = {'http': proxy, 'https': proxy}
    
    maximum_retries = 5
    
    try:
        # Get the file size for the progress bar
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        # Download the file in chunks and show progress
        with open(filepath, 'wb') as f, tqdm(
            desc=f"{index:02d} {filename}",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            bar_format='{l_bar}{bar:20}{r_bar}'
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    size = f.write(chunk)
                    bar.update(size)
        
        click.echo(click.style(f"✓ {filename} downloaded", fg="green"))
        return True
        
    except Exception as e:
        # Clean up partially downloaded file
        if os.path.exists(filepath):
            os.remove(filepath)
        click.echo(click.style(f"✗ Failed to download {filename}: {str(e)}", fg="red"))
        return False

def download_subtitles(index, subs, video_name, path, video_duration):
    """Write to a file (subtitle file) caption matching the right time."""
    with open(f"{path}/{index:02d} {clean_name(video_name).strip()}.srt", "wb") as f:
        click.echo("Downloading subtitles..")
        for i, sub in enumerate(subs, start=1):
            starts_at = sub["transcriptStartAt"]
            ends_at = subs[i]["transcriptStartAt"] if i < len(subs) else video_duration
            caption = sub["caption"]
            line = f"{i}\n{subtitles_time_format(starts_at)} --> {subtitles_time_format(ends_at)}\n{caption}\n\n"
            f.write(line.encode("utf8"))

def download_exercises(links, path, proxies=None):
    """
    Download exercise files.
    
    Args:
        links (list): List of exercise file URLs
        path (str): Directory path to save the exercise files
        proxies (list, optional): List of proxy URLs to use for the download
    """
    if not os.path.exists(path):
        os.makedirs(path)
    
    session = requests.Session()
    
    # Configure proxy if available
    if proxies and len(proxies) > 0:
        proxy = proxies[0] if isinstance(proxies, list) else proxies
        session.proxies = {'http': proxy, 'https': proxy}
    
    for link in links:
        try:
            filename = os.path.basename(link.split('?')[0])
            filepath = os.path.join(path, filename)
            
            # Skip if file already exists and has content
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                click.echo(click.style(f"✓ Exercise {filename} already exists", fg="green"))
                continue
            
            with session.get(link, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                with open(filepath, 'wb') as f, tqdm(
                    desc=f"Downloading {filename}",
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                    bar_format='{l_bar}{bar:20}{r_bar}'
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            size = f.write(chunk)
                            bar.update(size)
                
                click.echo(click.style(f"✓ Downloaded exercise: {filename}", fg="green"))
                
        except Exception as e:
            click.echo(click.style(f"✗ Failed to download exercise {link}: {str(e)}", fg="red"))
            continue