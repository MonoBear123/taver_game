import heapq

class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = 0  
        self.h = 0  
        self.f = 0  

    def __eq__(self, other):
        return self.position == other.position

    def __lt__(self, other):
        return self.f < other.f

def astar(grid, start, end):
    start_node = Node(start)
    end_node = Node(end)

    open_list = []
    closed_list = set()

    heapq.heappush(open_list, start_node)

    while open_list:
        current_node = heapq.heappop(open_list)
        closed_list.add(current_node.position)

        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1]  # Return reversed path

        (x, y) = current_node.position
        
        moves = [
            (0, -1, 1),      
            (0, 1, 1),       
            (-1, 0, 1),      
            (1, 0, 1),       
            (-1, -1, 1.414), 
            (1, -1, 1.414),  
            (-1, 1, 1.414),  
            (1, 1, 1.414)    
        ]

        for move_x, move_y, move_cost in moves:
            new_position = (x + move_x, y + move_y)
            (node_x, node_y) = new_position

            if not (0 <= node_y < len(grid) and 0 <= node_x < len(grid[0])):
                continue

            if grid[node_y][node_x] != 0:
                continue

            if move_x != 0 and move_y != 0:
                if grid[y][x + move_x] != 0 or grid[y + move_y][x] != 0:
                    continue
            
            if new_position in closed_list:
                continue

            new_node = Node(new_position, current_node)

            if new_node in open_list:
                continue
            
            new_node.g = current_node.g + move_cost
            new_node.h = abs(new_node.position[0] - end_node.position[0]) + \
                         abs(new_node.position[1] - end_node.position[1])  
            new_node.f = new_node.g + new_node.h
            
            heapq.heappush(open_list, new_node)

    return None  