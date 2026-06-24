import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# GitHub Config
USERNAME = "Mr-Hasan-Hamid"
# Read token from environment
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("INPUT_TOKEN")

LANGUAGE_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572a5",
    "Shell": "#89e051",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "C#": "#178600",
    "Go": "#00add8",
    "C++": "#f34b7d",
    "PLpgSQL": "#336791",
    "Java": "#b07219",
    "Scheme": "#1e4aec"
}
DEFAULT_COLOR = "#858585"

def make_request(url):
    """Helper to perform authenticated GitHub API requests using urllib."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Hasan-Hamid-Profile-Updater")
    req.add_header("Accept", "application/vnd.github.v3+json")
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error for {url}: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"Error making request to {url}: {e}")
        return None

def get_relative_time(date_str):
    """Convert ISO timestamp to human-readable relative time."""
    try:
        # date_str is like '2026-06-24T15:25:25Z'
        dt = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        except ImportError:
            now = datetime.utcnow()
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{int(seconds)}s ago"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)}m ago"
        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)}h ago"
        days = hours / 24
        if days < 30:
            if int(days) == 1:
                return "yesterday"
            return f"{int(days)} days ago"
        months = days / 30
        if months < 12:
            return f"{int(months)} months ago"
        return f"{int(months / 12)} years ago"
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return date_str

def fetch_languages_and_repos():
    """Fetch repositories and aggregate their languages."""
    print("Fetching repositories...")
    # Get all repos (public or private depending on GITHUB_TOKEN scope)
    # Using /user/repos if token is set, otherwise fallback to public repos
    url = f"https://api.github.com/user/repos?per_page=100&sort=updated" if TOKEN else f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"
    repos = make_request(url)
    
    if not repos:
        print("Warning: Repos list empty. Falling back to public /users endpoint.")
        repos = make_request(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated")
        
    if not repos:
        print("Error: Could not retrieve repositories.")
        return [], {}

    # Sort out forks and profile README repo
    filtered_repos = []
    lang_totals = {}
    
    for r in repos:
        # Check owner is Mr-Hasan-Hamid to avoid showing starred/contributed repos in personal stats
        if r.get("owner", {}).get("login").lower() != USERNAME.lower():
            continue
        # Allow forks only if they have stars (e.g. customized forks like Arch-Hyprlands)
        if r.get("fork") and r.get("stargazers_count", 0) == 0:
            continue
            
        filtered_repos.append(r)
        
        # Query specific language sizes for this repo to get high accuracy stats
        lang_url = r.get("languages_url")
        if lang_url:
            lang_data = make_request(lang_url)
            if lang_data:
                r["languages_map"] = lang_data
                for lang, bytes_count in lang_data.items():
                    lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
            else:
                # Fallback to primary language and size if API fails
                prim_lang = r.get("language")
                if prim_lang:
                    # Size is in KB, estimate bytes
                    size_bytes = r.get("size", 0) * 1024
                    lang_totals[prim_lang] = lang_totals.get(prim_lang, 0) + size_bytes

    return filtered_repos, lang_totals

def generate_language_svg(lang_totals):
    """Generate custom languages.svg progress bar."""
    if not lang_totals:
        return
        
    total_bytes = sum(lang_totals.values())
    if total_bytes == 0:
        return
        
    # Sort languages by size
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate percentages and filter top languages
    top_languages = []
    other_bytes = 0
    for idx, (lang, size) in enumerate(sorted_langs):
        pct = (size / total_bytes) * 100
        if pct >= 1.0 or idx < 5:  # Keep languages >= 1% or top 5
            top_languages.append((lang, size, pct, LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)))
        else:
            other_bytes += size
            
    if other_bytes > 0:
        pct = (other_bytes / total_bytes) * 100
        top_languages.append(("Other", other_bytes, pct, DEFAULT_COLOR))
        
    # Start SVG content
    bar_height = 10
    rx = 5
    bar_width = 800
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 65" width="100%">
  <defs>
    <clipPath id="bar-clip">
      <rect width="{bar_width}" height="{bar_height}" rx="{rx}" />
    </clipPath>
  </defs>
  <g clip-path="url(#bar-clip)">
"""
    current_x = 0
    for lang, _, pct, color in top_languages:
        width = (pct / 100.0) * bar_width
        svg_content += f'    <rect x="{current_x:.2f}" y="0" width="{width:.2f}" height="{bar_height}" fill="{color}" />\n'
        current_x += width
        
    svg_content += "  </g>\n"
    
    # Render legend (2 rows of 3 columns max)
    for idx, (lang, _, pct, color) in enumerate(top_languages[:6]):
        col = idx % 3
        row = idx // 3
        x = 10 + col * 260
        y = 35 + row * 20
        svg_content += f'  <circle cx="{x}" cy="{y-4}" r="5" fill="{color}" />\n'
        svg_content += f'  <text x="{x+12}" y="{y}" font-family="system-ui, -apple-system, sans-serif" font-size="12" fill="#c9d1d9" font-weight="500">{lang} <tspan fill="#8b949e">({pct:.1f}%)</tspan></text>\n'
        
    svg_content += "</svg>"
    
    # Save the SVG
    try:
        with open("languages.svg", "w", encoding="utf-8") as f:
            f.write(svg_content)
        print("Generated languages.svg successfully.")
    except Exception as e:
        print(f"Error saving languages.svg: {e}")

def fetch_activity():
    """Fetch user's public activities."""
    print("Fetching activity...")
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    events = make_request(url)
    
    if not events:
        print("Error: Could not retrieve activity.")
        return "No recent activity found."
        
    activity_lines = []
    seen_commits = set() # Avoid listing duplicate push commits if any
    
    for event in events:
        if len(activity_lines) >= 5:
            break
            
        e_type = event.get("type")
        repo_name = event.get("repo", {}).get("name")
        repo_url = f"https://github.com/{repo_name}"
        time_str = get_relative_time(event.get("created_at"))
        
        # Simplify repo name
        repo_short = repo_name.replace(f"{USERNAME}/", "")
        
        payload = event.get("payload", {})
        
        if e_type == "PushEvent":
            head_sha = payload.get("head")
            if head_sha and head_sha not in seen_commits:
                seen_commits.add(head_sha)
                commit_details = make_request(f"https://api.github.com/repos/{repo_name}/commits/{head_sha}")
                if commit_details:
                    commit_msg = commit_details.get("commit", {}).get("message", "Commit").split("\n")[0]
                    # Escape html characters in commit message just in case
                    commit_msg = commit_msg.replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')
                    sha_short = head_sha[:7]
                    commit_url = f"https://github.com/{repo_name}/commit/{head_sha}"
                    activity_lines.append(f"<li>📝 Committed to <a href=\"{repo_url}\"><b>{repo_short}</b></a>: <a href=\"{commit_url}\"><code>{sha_short}</code></a> <i>\"{commit_msg}\"</i> ({time_str})</li>")
                        
        elif e_type == "PullRequestEvent":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            pr_title = pr.get("title")
            pr_url = pr.get("html_url")
            pr_num = pr.get("number")
            
            icon = "🔀"
            if action == "opened":
                icon = "⚙️"
            elif action == "closed" and pr.get("merged"):
                icon = "🎉"
                action = "merged"
                
            activity_lines.append(f"<li>{icon} {action.capitalize()} PR <a href=\"{pr_url}\"><b>#{pr_num}</b></a> in <a href=\"{repo_url}\"><b>{repo_short}</b></a>: <i>\"{pr_title}\"</i> ({time_str})</li>")
            
        elif e_type == "IssuesEvent":
            action = payload.get("action")
            issue = payload.get("issue", {})
            issue_title = issue.get("title")
            issue_url = issue.get("html_url")
            issue_num = issue.get("number")
            
            icon = "🐛" if action == "opened" else "✅"
            activity_lines.append(f"<li>{icon} {action.capitalize()} Issue <a href=\"{issue_url}\"><b>#{issue_num}</b></a> in <a href=\"{repo_url}\"><b>{repo_short}</b></a>: <i>\"{issue_title}\"</i> ({time_str})</li>")
            
        elif e_type == "WatchEvent":
            activity_lines.append(f"<li>⭐ Starred repository <a href=\"{repo_url}\"><b>{repo_name}</b></a> ({time_str})</li>")
            
        elif e_type == "CreateEvent":
            ref_type = payload.get("ref_type")
            if ref_type == "repository":
                activity_lines.append(f"<li>✨ Created new repository <a href=\"{repo_url}\"><b>{repo_short}</b></a> ({time_str})</li>")
            else:
                ref = payload.get("ref")
                activity_lines.append(f"<li>🌿 Created branch/tag <code>{ref}</code> in <a href=\"{repo_url}\"><b>{repo_short}</b></a> ({time_str})</li>")

    if not activity_lines:
        return "No recent activity found."
        
    return "<ul>\n" + "\n".join(activity_lines) + "\n</ul>"

def generate_repo_showcase(repos):
    """Generate beautiful grid structure for top repositories."""
    # Filter public repositories to showcase
    public_repos = [r for r in repos if not r.get("private")]
    
    # Sort repos: star count desc, then size desc
    public_repos.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("size", 0)), reverse=True)
    
    # We want to display up to 6 repositories in a nice 2-column table
    showcase_repos = public_repos[:6]
    
    html = '<table width="100%" style="border-collapse: collapse; border: none;">\n'
    
    for idx in range(0, len(showcase_repos), 2):
        html += '  <tr style="border: none;">\n'
        for col_idx in range(2):
            repo_idx = idx + col_idx
            if repo_idx < len(showcase_repos):
                r = showcase_repos[repo_idx]
                name = r.get("name")
                desc = r.get("description") or "No description provided."
                lang = r.get("language")
                if not lang and r.get("languages_map"):
                    lang = max(r["languages_map"].items(), key=lambda x: x[1])[0]
                if not lang:
                    lang = "Other"
                stars = r.get("stargazers_count", 0)
                forks = r.get("forks_count", 0)
                url = r.get("html_url")
                
                lang_color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)
                
                # Truncate description if too long
                if len(desc) > 85:
                    desc = desc[:82] + "..."
                    
                html += f'''    <td width="50%" valign="top" style="border: 1px solid #21262d; border-radius: 6px; padding: 15px; background: #0d1117;">
      <h3 style="margin-top: 0; margin-bottom: 8px;"><a href="{url}" style="text-decoration: none; color: #58a6ff;">📁 {name}</a></h3>
      <p style="font-size: 13px; color: #8b949e; height: 38px; margin-bottom: 12px; overflow: hidden; line-height: 1.4;">{desc}</p>
      <div style="font-size: 12px; color: #8b949e; display: flex; align-items: center; gap: 15px;">
        <span style="display: inline-flex; align-items: center; gap: 4px;">
          <circle cx="6" cy="6" r="4" fill="{lang_color}" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: {lang_color}; margin-right: 4px;"></circle>{lang}
        </span>
        <span>⭐ {stars}</span>
        <span>🍴 {forks}</span>
      </div>
    </td>\n'''
            else:
                html += '    <td width="50%" style="border: none; background: transparent;"></td>\n'
        html += '  </tr>\n'
        
    html += '</table>'
    return html

def update_readme(activity_html, repo_html):
    """Replace designated placeholders in README.md with generated content."""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: README.md not found.")
        return

    # Replace activity
    start_tag = "<!-- START_SECTION:activity -->"
    end_tag = "<!-- END_SECTION:activity -->"
    if start_tag in content and end_tag in content:
        start_idx = content.find(start_tag) + len(start_tag)
        end_idx = content.find(end_tag)
        content = content[:start_idx] + "\n" + activity_html + "\n" + content[end_idx:]
        
    # Replace repositories
    start_tag_repos = "<!-- START_SECTION:repos -->"
    end_tag_repos = "<!-- END_SECTION:repos -->"
    if start_tag_repos in content and end_tag_repos in content:
        start_idx = content.find(start_tag_repos) + len(start_tag_repos)
        end_idx = content.find(end_tag_repos)
        content = content[:start_idx] + "\n" + repo_html + "\n" + content[end_idx:]

    try:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(content)
        print("README.md updated successfully.")
    except Exception as e:
        print(f"Error writing to README.md: {e}")

def main():
    print("Starting profile updater...")
    
    # 1. Fetch repos and calculate languages
    repos, lang_totals = fetch_languages_and_repos()
    
    # 2. Generate languages.svg
    if lang_totals:
        generate_language_svg(lang_totals)
    else:
        print("Skipping languages.svg generation due to missing language stats.")
        
    # 3. Fetch activity
    activity_html = fetch_activity()
    
    # 4. Generate repo showcase
    repo_html = ""
    if repos:
        repo_html = generate_repo_showcase(repos)
        
    # 5. Update README.md
    update_readme(activity_html, repo_html)
    print("All tasks completed.")

if __name__ == "__main__":
    main()
