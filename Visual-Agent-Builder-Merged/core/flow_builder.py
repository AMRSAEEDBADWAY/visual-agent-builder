"""
Flow Builder — Core logic for managing visual agent flows.
Handles CRUD operations on nodes (agents) and edges (connections),
flow validation, topological sorting, and auto-layout.
"""

import json
import uuid
from collections import defaultdict, deque
from typing import Optional
from core.database import (
    get_db_connection, save_node, get_nodes, save_edge, get_edges,
    create_project, get_projects_by_user, get_project, delete_project
)

# ─────────────────────── Agent Colors ────────────────────────
AGENT_COLORS = [
    "#6C5CE7", "#00B894", "#E17055", "#0984E3",
    "#FDCB6E", "#E84393", "#00CEC9", "#D63031",
    "#A29BFE", "#55EFC4", "#FAB1A0", "#74B9FF",
]

AGENT_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash-preview-04-17",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

DEFAULT_TOOLS = [
    "google_search",
    "calculator",
    "get_current_time",
    "save_artifact",
    "load_artifact",
    "vision_analyze",
]


# ═══════════════════════ FlowBuilder ═══════════════════════
class FlowBuilder:
    """
    Manages the visual flow of agents for a given project.
    All data is persisted via the SQLite helpers in database.py.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id

    # ──────────── Node / Agent helpers ────────────

    @staticmethod
    def _make_data_json(
        instructions: str = "",
        model: str = "gemini-2.0-flash",
        tools: list | None = None,
        description: str = "",
        agent_type: str = "agent",
        color: str = "#6C5CE7",
    ) -> str:
        """Serialize agent metadata to a JSON string for the DB."""
        return json.dumps({
            "instructions": instructions,
            "model": model,
            "tools": tools or [],
            "description": description,
            "agent_type": agent_type,
            "color": color,
        }, ensure_ascii=False)

    @staticmethod
    def _parse_data_json(raw: str | None) -> dict:
        """Deserialize the JSON blob stored on a node row."""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    # ──────────── CRUD: Agents (Nodes) ────────────

    def add_agent(
        self,
        name: str,
        x: float = 100.0,
        y: float = 100.0,
        instructions: str = "",
        model: str = "gemini-2.0-flash",
        tools: list | None = None,
        description: str = "",
        color: str | None = None,
    ) -> str:
        """Create a new agent node and persist it. Returns the new node id."""
        node_id = str(uuid.uuid4())
        if color is None:
            # Pick a colour based on how many nodes already exist
            existing = self.get_agents()
            color = AGENT_COLORS[len(existing) % len(AGENT_COLORS)]

        data = self._make_data_json(
            instructions=instructions,
            model=model,
            tools=tools,
            description=description,
            color=color,
        )
        save_node(node_id, self.project_id, name, "agent", x, y, data)
        return node_id

    def update_agent(
        self,
        node_id: str,
        name: str | None = None,
        x: float | None = None,
        y: float | None = None,
        instructions: str | None = None,
        model: str | None = None,
        tools: list | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> bool:
        """Update an existing agent node. Only provided fields are changed."""
        agents = {a["id"]: a for a in self.get_agents()}
        if node_id not in agents:
            return False

        row = agents[node_id]
        current = self._parse_data_json(row["data_json"])

        final_name = name if name is not None else row["name"]
        final_x = x if x is not None else row["x_position"]
        final_y = y if y is not None else row["y_position"]

        new_data = self._make_data_json(
            instructions=instructions if instructions is not None else current.get("instructions", ""),
            model=model if model is not None else current.get("model", "gemini-2.0-flash"),
            tools=tools if tools is not None else current.get("tools", []),
            description=description if description is not None else current.get("description", ""),
            color=color if color is not None else current.get("color", "#6C5CE7"),
        )
        save_node(node_id, self.project_id, final_name, "agent", final_x, final_y, new_data)
        return True

    def delete_agent(self, node_id: str) -> bool:
        """Delete an agent node and its connected edges."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM edges WHERE project_id = ? AND (source_node_id = ? OR target_node_id = ?)",
                         (self.project_id, node_id, node_id))
            cursor = conn.execute("DELETE FROM nodes WHERE id = ? AND project_id = ?", (node_id, self.project_id))
            return cursor.rowcount > 0

    def get_agents(self) -> list[dict]:
        """Return all agent nodes for this project as dicts."""
        rows = get_nodes(self.project_id)
        agents = []
        for r in rows:
            d = dict(r)
            d["meta"] = self._parse_data_json(d.get("data_json"))
            agents.append(d)
        return agents

    # ──────────── CRUD: Edges ────────────

    def add_edge(self, source_id: str, target_id: str) -> str:
        """Create a directed edge between two nodes. Returns edge id."""
        edge_id = str(uuid.uuid4())
        save_edge(edge_id, self.project_id, source_id, target_id)
        return edge_id

    def delete_edge(self, edge_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM edges WHERE id = ? AND project_id = ?", (edge_id, self.project_id))
            return cursor.rowcount > 0

    def get_edges_list(self) -> list[dict]:
        rows = get_edges(self.project_id)
        return [dict(r) for r in rows]

    # ──────────── Full flow data ────────────

    def get_flow_data(self) -> dict:
        """Return the complete flow (nodes + edges) as a serialisable dict."""
        agents = self.get_agents()
        edges = self.get_edges_list()
        return {
            "project_id": self.project_id,
            "agents": agents,
            "edges": edges,
        }

    def clear_flow(self) -> None:
        """Delete every node and edge in this project."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM edges WHERE project_id = ?", (self.project_id,))
            conn.execute("DELETE FROM nodes WHERE project_id = ?", (self.project_id,))

    # ──────────── Validation ────────────

    def validate_flow(self) -> list[str]:
        """Return a list of human-readable warnings about the current flow."""
        warnings: list[str] = []
        agents = self.get_agents()
        edges = self.get_edges_list()

        if not agents:
            warnings.append("⚠️ لا يوجد أي Agent في المشروع.")
            return warnings

        node_ids = {a["id"] for a in agents}

        # Orphan edges
        for e in edges:
            if e["source_node_id"] not in node_ids:
                warnings.append(f"⚠️ سهم يشير من عقدة غير موجودة ({e['source_node_id'][:8]}…)")
            if e["target_node_id"] not in node_ids:
                warnings.append(f"⚠️ سهم يشير إلى عقدة غير موجودة ({e['target_node_id'][:8]}…)")

        # Disconnected agents
        connected = set()
        for e in edges:
            connected.add(e["source_node_id"])
            connected.add(e["target_node_id"])
        for a in agents:
            if a["id"] not in connected and len(agents) > 1:
                warnings.append(f"⚠️ العميل «{a['name']}» غير متصل بأي سهم.")

        # Cycle detection
        if self._has_cycle(agents, edges):
            warnings.append("🔄 يوجد حلقة دائرية (Cycle) في التدفق. تأكد من عدم وجود مسار يعود لنقطة البداية.")

        return warnings

    # ──────────── Topological Sort ────────────

    def get_execution_order(self) -> list[str]:
        """
        Return node IDs in topological order (Kahn's algorithm).
        If a cycle exists, returns as many nodes as possible.
        """
        agents = self.get_agents()
        edges = self.get_edges_list()

        in_degree: dict[str, int] = {a["id"]: 0 for a in agents}
        adj: dict[str, list[str]] = defaultdict(list)

        for e in edges:
            src, tgt = e["source_node_id"], e["target_node_id"]
            if src in in_degree and tgt in in_degree:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbour in adj[nid]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        return order

    def _has_cycle(self, agents: list[dict], edges: list[dict]) -> bool:
        order = self.get_execution_order()
        return len(order) < len(agents)

    # ──────────── Auto-layout ────────────

    def auto_layout(self, start_x: float = 80, start_y: float = 80,
                    gap_x: float = 280, gap_y: float = 160) -> None:
        """
        Arrange agents in a left-to-right layered layout based on
        topological order, then persist the new positions.
        """
        order = self.get_execution_order()
        agents = {a["id"]: a for a in self.get_agents()}
        edges = self.get_edges_list()

        # Build depth map
        depth: dict[str, int] = {}
        for nid in order:
            depth[nid] = 0
        for nid in order:
            for e in edges:
                if e["source_node_id"] == nid and e["target_node_id"] in depth:
                    depth[e["target_node_id"]] = max(depth[e["target_node_id"]], depth[nid] + 1)

        # Group by depth
        layers: dict[int, list[str]] = defaultdict(list)
        for nid, d in depth.items():
            layers[d].append(nid)

        # Assign positions
        for d, nids in layers.items():
            for i, nid in enumerate(nids):
                if nid in agents:
                    new_x = start_x + d * gap_x
                    new_y = start_y + i * gap_y
                    a = agents[nid]
                    save_node(nid, self.project_id, a["name"], "agent", new_x, new_y, a["data_json"])

        # Place any unvisited nodes (disconnected)
        placed = set(depth.keys())
        row = 0
        max_depth = max(depth.values(), default=0) + 1
        for nid, a in agents.items():
            if nid not in placed:
                nx = start_x + max_depth * gap_x
                ny = start_y + row * gap_y
                save_node(nid, self.project_id, a["name"], "agent", nx, ny, a["data_json"])
                row += 1

    # ──────────── Export ────────────

    def export_flow_json(self) -> str:
        """Export the full flow as a formatted JSON string."""
        data = self.get_flow_data()
        # Strip internal DB keys for a clean export
        clean_agents = []
        for a in data["agents"]:
            meta = a.get("meta", {})
            clean_agents.append({
                "id": a["id"],
                "name": a["name"],
                "x": a["x_position"],
                "y": a["y_position"],
                "instructions": meta.get("instructions", ""),
                "model": meta.get("model", ""),
                "tools": meta.get("tools", []),
                "description": meta.get("description", ""),
                "color": meta.get("color", "#6C5CE7"),
            })
        clean_edges = []
        for e in data["edges"]:
            clean_edges.append({
                "id": e["id"],
                "source": e["source_node_id"],
                "target": e["target_node_id"],
            })
        return json.dumps({
            "project_id": self.project_id,
            "agents": clean_agents,
            "edges": clean_edges,
        }, ensure_ascii=False, indent=2)

    def import_flow_json(self, json_str: str) -> None:
        """Import a flow from a JSON string (clears existing flow first)."""
        data = json.loads(json_str)
        self.clear_flow()

        for a in data.get("agents", []):
            data_json = self._make_data_json(
                instructions=a.get("instructions", ""),
                model=a.get("model", "gemini-2.0-flash"),
                tools=a.get("tools", []),
                description=a.get("description", ""),
                color=a.get("color", "#6C5CE7"),
            )
            save_node(
                a["id"], self.project_id, a["name"], "agent",
                a.get("x", 100), a.get("y", 100), data_json,
            )

        for e in data.get("edges", []):
            save_edge(e["id"], self.project_id, e["source"], e["target"])
