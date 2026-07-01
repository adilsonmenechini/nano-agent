// Modern SkillManager — search, status badges, grouped categories, optimistic updates

class SkillManager {
  constructor(container) {
    this.container = container;
    this.skills = [];
    this.enabledMap = new Map();
    this._searchTerm = '';
  }

  async loadSkills() {
    try {
      const req = fetch('/api/skills');
      const resp = await req;
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      this.skills = data.skills || [];
      for (const s of this.skills) {
        this.enabledMap.set(s.name, s.enabled !== false);
      }
      this.render();
    } catch (e) {
      console.error('Failed to load skills', e);
    }
  }

  async toggle(name, checked) {
    this.enabledMap.set(name, checked);
    this.render();
    try {
      const resp = await fetch(`/api/skills/${encodeURIComponent(name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: checked }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    } catch (e) {
      this.enabledMap.set(name, !checked);
      this.render();
      console.error('Failed to toggle skill', e);
    }
  }

  setSearch(term) {
    this._searchTerm = term.trim().toLowerCase();
    this.render();
  }

  _categorize(skill) {
    const name = (skill.name || '').toLowerCase();
    if (name.includes('tool')) return 'Tools';
    if (name.includes('reflection') || name.includes('introspection')) return 'Reflection';
    if (name.includes('learning') || name.includes('evolution')) return 'Learning';
    return 'General';
  }

  render() {
    this.container.innerHTML = '';
    const query = this._searchTerm;
    const matches = this.skills.filter(s => {
      if (!query) return true;
      const hay = `${s.name} ${s.description || ''}`.toLowerCase();
      return hay.includes(query);
    });

    if (matches.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'skills-empty';
      empty.textContent = query ? 'No matching skills' : 'No skills installed';
      this.container.appendChild(empty);
      return;
    }

    const groups = new Map();
    for (const s of matches) {
      const label = this._categorize(s);
      const list = groups.get(label) || [];
      list.push(s);
      groups.set(label, list);
    }

    for (const [label, list] of groups) {
      const groupHeader = document.createElement('div');
      groupHeader.className = 'skills-group-label';
      groupHeader.textContent = label;
      this.container.appendChild(groupHeader);

      for (const s of list) {
        const item = document.createElement('div');
        item.className = 'skill-item';

        const info = document.createElement('div');
        info.className = 'skill-info';

        const name = document.createElement('div');
        name.className = 'skill-name';
        name.textContent = s.name;

        const desc = document.createElement('div');
        desc.className = 'skill-desc';
        desc.textContent = s.description || '—';

        info.appendChild(name);
        info.appendChild(desc);

        const status = document.createElement('span');
        status.className = 'skill-status';
        status.textContent = this.enabledMap.get(s.name) ? 'Active' : 'Disabled';

        const toggle = document.createElement('label');
        toggle.className = 'toggle-switch';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = this.enabledMap.get(s.name) !== false;
        input.addEventListener('change', () => this.toggle(s.name, input.checked));

        const slider = document.createElement('span');
        slider.className = 'toggle-slider';

        toggle.appendChild(input);
        toggle.appendChild(slider);

        item.appendChild(info);
        item.appendChild(status);
        item.appendChild(toggle);
        this.container.appendChild(item);
      }
    }
  }
}