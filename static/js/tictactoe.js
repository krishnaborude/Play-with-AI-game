// DOM Elements
const board = document.querySelector('.board');
const cells = document.querySelectorAll('[data-cell]');
const status = document.getElementById('status');
const playerScoreElement = document.getElementById('playerScore');
const aiScoreElement = document.getElementById('aiScore');
const drawScoreElement = document.getElementById('drawScore');
const resultOverlay = document.getElementById('resultOverlay');
const resultText = document.getElementById('resultText');
const playAgainBtn = document.getElementById('playAgainBtn');

// Game state
let currentPlayer = 'X';
let gameActive = true;
let gameState = ['', '', '', '', '', '', '', '', ''];
let scores = {
    player: 0,
    ai: 0,
    draws: 0
};

// Winning combinations
const winningConditions = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8], // Columns
    [0, 4, 8], [2, 4, 6] // Diagonals
];

// Position weights for better strategic decisions
const positionWeights = [
    5, 3, 5,  // Corners have highest weight now
    3, 4, 3,  // Center and edges balanced
    5, 3, 5   // Corners critical for winning
];

// Pattern recognition for advanced strategies
const winningPatterns = {
    corner_trap: [[0, 8], [2, 6]], // Opposite corners
    edge_trap: [[1, 7], [3, 5]],   // Opposite edges
    triangle_trap: [[0, 2, 6], [0, 6, 8], [2, 6, 8], [0, 2, 8]] // Triangle formations
};

// Load scores from database
async function loadScores() {
    try {
        console.log('Loading scores from database...');
        const response = await fetch('/api/game-scores?game_type=tictactoe');
        if (!response.ok) {
            throw new Error('Failed to fetch game scores');
        }
        
        const data = await response.json();
        console.log('Received scores data:', data);
        scores = data;
        updateScoreDisplay();
        
        // Show a brief notification that scores were loaded
        const userEmail = document.querySelector('.user-email')?.textContent || 'your account';
        showNotification(`Game statistics loaded for ${userEmail}`);
    } catch (error) {
        console.error('Error loading game scores:', error);
    }
}

// Show a brief notification
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'score-notification';
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.bottom = '20px';
    notification.style.left = '50%';
    notification.style.transform = 'translateX(-50%)';
    notification.style.padding = '10px 20px';
    notification.style.backgroundColor = 'var(--primary-color)';
    notification.style.color = 'white';
    notification.style.borderRadius = '8px';
    notification.style.boxShadow = 'var(--shadow-md)';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease';
    
    document.body.appendChild(notification);
    
    // Fade in
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    // Fade out and remove
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Update score display
function updateScoreDisplay() {
    playerScoreElement.textContent = scores.player;
    aiScoreElement.textContent = scores.ai;
    drawScoreElement.textContent = scores.draws;
}

// Reset scores in the database
async function resetScores() {
    try {
        const formData = new FormData();
        formData.append('game_type', 'tictactoe');
        
        const response = await fetch('/api/reset-game-scores', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to reset scores');
        }
        
        const data = await response.json();
        scores = {
            player: 0,
            ai: 0,
            draws: 0
        };
        
        updateScoreDisplay();
        showNotification('Game scores have been reset');
        
    } catch (error) {
        console.error('Error resetting scores:', error);
        showNotification('Failed to reset scores, please try again');
    }
}

// Handle cell click
function handleCellClick(e) {
    const cell = e.target;
    const index = Array.from(cells).indexOf(cell);

    if (gameState[index] !== '' || !gameActive) return;

    // Player move
    makeMove(index, 'X');

    if (checkWin('X')) {
        endGame('player');
        return;
    }

    if (checkDraw()) {
        endGame('draw');
        return;
    }

    // AI's turn
    status.textContent = "AI's turn (O)";
    setTimeout(() => {
        makeAIMove();
    }, 500);
}

// Make a move
function makeMove(index, player) {
    gameState[index] = player;
    cells[index].textContent = player;
    cells[index].classList.add(player.toLowerCase());
}

// AI move
function makeAIMove() {
    if (!gameActive) return;

    const index = findBestMove();
    makeMove(index, 'O');

    if (checkWin('O')) {
        endGame('ai');
        return;
    }

    if (checkDraw()) {
        endGame('draw');
        return;
    }

    status.textContent = "Your turn (X)";
}

// Enhanced minimax with advanced evaluation
function minimax(board, depth, isMaximizing, alpha, beta) {
    // Increase depth limit for better lookahead
    const maxDepth = 9;
    if (depth >= maxDepth) return evaluatePosition(board);

    // Terminal states with higher scores
    if (checkWinForMinimax(board, 'O')) return 1000 - depth;
    if (checkWinForMinimax(board, 'X')) return depth - 1000;
    if (checkDrawForMinimax(board)) return 0;

    if (isMaximizing) {
        let bestScore = -Infinity;
        const moveOrder = getMoveOrder(board);
        
        for (const i of moveOrder) {
            if (board[i] === '') {
                board[i] = 'O';
                let score = minimax(board, depth + 1, false, alpha, beta);
                board[i] = '';
                score += evaluateMove(board, i, 'O', depth);
                bestScore = Math.max(score, bestScore);
                alpha = Math.max(alpha, bestScore);
                if (beta <= alpha) break;
            }
        }
        return bestScore;
    } else {
        let bestScore = Infinity;
        const moveOrder = getMoveOrder(board);
        
        for (const i of moveOrder) {
            if (board[i] === '') {
                board[i] = 'X';
                let score = minimax(board, depth + 1, true, alpha, beta);
                board[i] = '';
                score -= evaluateMove(board, i, 'X', depth);
                bestScore = Math.min(score, bestScore);
                beta = Math.min(beta, bestScore);
                if (beta <= alpha) break;
            }
        }
        return bestScore;
    }
}

// Evaluate the current board position
function evaluatePosition(board) {
    let score = 0;
    
    // Evaluate piece positions
    for (let i = 0; i < board.length; i++) {
        if (board[i] === 'O') score += positionWeights[i];
        else if (board[i] === 'X') score -= positionWeights[i];
    }
    
    // Check for potential wins
    score += evaluatePotentialWins(board, 'O') * 10;
    score -= evaluatePotentialWins(board, 'X') * 8;
    
    // Check for traps
    score += evaluateTraps(board) * 15;
    
    return score;
}

// Evaluate potential winning moves
function evaluatePotentialWins(board, player) {
    let score = 0;
    winningConditions.forEach(condition => {
        const line = condition.map(index => board[index]);
        const playerCount = line.filter(cell => cell === player).length;
        const emptyCount = line.filter(cell => cell === '').length;
        
        if (playerCount === 2 && emptyCount === 1) score += 5;
        if (playerCount === 1 && emptyCount === 2) score += 2;
    });
    return score;
}

// Evaluate traps and strategic patterns
function evaluateTraps(board) {
    let score = 0;
    
    // Check corner traps
    winningPatterns.corner_trap.forEach(trap => {
        if (trap.every(pos => board[pos] === 'O')) score += 8;
    });
    
    // Check triangle traps
    winningPatterns.triangle_trap.forEach(trap => {
        const trapPieces = trap.filter(pos => board[pos] === 'O').length;
        if (trapPieces >= 2) score += 6;
    });
    
    return score;
}

// Get optimized move order based on current board state
function getMoveOrder(board) {
    const moves = [];
    const corners = [0, 2, 6, 8];
    const edges = [1, 3, 5, 7];
    const center = 4;
    
    // Prioritize center
    if (board[center] === '') moves.push(center);
    
    // Then corners
    corners.forEach(pos => {
        if (board[pos] === '') moves.push(pos);
    });
    
    // Then edges
    edges.forEach(pos => {
        if (board[pos] === '') moves.push(pos);
    });
    
    return moves;
}

// Evaluate specific move
function evaluateMove(board, pos, player, depth) {
    let score = positionWeights[pos];
    
    // Check if move creates fork
    if (checkForkOpportunity(board, pos, player)) {
        score += 100 - depth * 10;
    }
    
    // Check if move blocks opponent's fork
    const opponent = player === 'O' ? 'X' : 'O';
    if (checkForkOpportunity(board, pos, opponent)) {
        score += 80 - depth * 8;
    }
    
    // Check if move is part of a trap
    if (isPartOfTrap(board, pos, player)) {
        score += 50 - depth * 5;
    }
    
    return score;
}

// Check if move is part of a strategic trap
function isPartOfTrap(board, pos, player) {
    for (const pattern in winningPatterns) {
        const patterns = winningPatterns[pattern];
        for (const trap of patterns) {
            if (trap.includes(pos)) {
                const otherPositions = trap.filter(p => p !== pos);
                if (otherPositions.some(p => board[p] === player)) {
                    return true;
                }
            }
        }
    }
    return false;
}

// Find best move for AI using enhanced minimax
function findBestMove() {
    let bestScore = -Infinity;
    let bestMove = -1;
    
    // First move optimization
    const emptyCount = gameState.filter(cell => cell === '').length;
    if (emptyCount === 9) {
        // First move: prefer corners for more aggressive play
        return [0, 2, 6, 8][Math.floor(Math.random() * 4)];
    }
    
    // Check for immediate win
    const winMove = findWinningMove('O');
    if (winMove !== -1) return winMove;
    
    // Check for immediate block
    const blockMove = findWinningMove('X');
    if (blockMove !== -1) return blockMove;
    
    // Use enhanced minimax with advanced evaluation
    const moveOrder = getMoveOrder(gameState);
    for (const i of moveOrder) {
        if (gameState[i] === '') {
            gameState[i] = 'O';
            let score = minimax(gameState, 0, false, -Infinity, Infinity);
            gameState[i] = '';
            
            // Add advanced evaluation scores
            score += evaluateMove(gameState, i, 'O', 0);
            
            if (score > bestScore) {
                bestScore = score;
                bestMove = i;
            }
        }
    }
    
    return bestMove !== -1 ? bestMove : moveOrder[0];
}

// Find winning move for a player
function findWinningMove(player) {
    for (let i = 0; i < gameState.length; i++) {
        if (gameState[i] === '') {
            gameState[i] = player;
            if (checkWin(player)) {
                gameState[i] = '';
                return i;
            }
            gameState[i] = '';
        }
    }
    return -1;
}

// Check for win
function checkWin(player) {
    return winningConditions.some(condition => {
        return condition.every(index => gameState[index] === player);
    });
}

// Check for draw
function checkDraw() {
    return gameState.every(cell => cell !== '');
}

// Highlight winning cells
function highlightWinningCells(player) {
    winningConditions.forEach(condition => {
        if (condition.every(index => gameState[index] === player)) {
            condition.forEach(index => {
                cells[index].classList.add('win');
            });
        }
    });
}

// End game
function endGame(result) {
    gameActive = false;
    let message = '';
    let statMessage = '';
    
    switch(result) {
        case 'player':
            message = "Congratulations! You win!";
            scores.player++;
            statMessage = "Win added to your stats!";
            highlightWinningCells('X');
            break;
        case 'ai':
            message = "AI wins! Try again!";
            scores.ai++;
            statMessage = "Loss added to your stats!";
            highlightWinningCells('O');
            break;
        case 'draw':
            message = "It's a draw!";
            scores.draws++;
            statMessage = "Draw added to your stats!";
            break;
    }
    
    updateScoreDisplay();
    status.textContent = message;
    resultText.textContent = message;
    
    // Show the result overlay
    if (resultOverlay) {
        resultOverlay.classList.add('show');
    }

    // Show notification for stats update
    setTimeout(() => {
        showNotification(statMessage);
    }, 1000);

    // Save the game result to database
    const moves = getGameMoves();
    saveGameResult(result, moves);
}

// Restart game
function restartGame() {
    // Clear the board
    gameState = ['', '', '', '', '', '', '', '', ''];
    gameActive = true;
    currentPlayer = 'X';
    
    // Reset UI
    cells.forEach(cell => {
        cell.textContent = '';
        cell.classList.remove('x', 'o', 'win');
    });
    
    status.textContent = "Your turn (X)";
    
    // Hide the result overlay
    if (resultOverlay) {
        resultOverlay.classList.remove('show');
    }
}

// Initialize game
function initGame() {
    // Initialize scores from hidden fields first
    const winsElement = document.getElementById('stats-wins');
    const lossesElement = document.getElementById('stats-losses');
    const drawsElement = document.getElementById('stats-draws');
    
    if (winsElement && lossesElement && drawsElement) {
        scores = {
            player: parseInt(winsElement.value) || 0,
            ai: parseInt(lossesElement.value) || 0,
            draws: parseInt(drawsElement.value) || 0
        };
        updateScoreDisplay();
    }
    
    // Then load from API to ensure we have the latest data
    loadScores();
    
    // Add click event listeners to cells
    cells.forEach(cell => {
        cell.addEventListener('click', handleCellClick);
    });
    
    // Add click event listener to play again button
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', restartGame);
    }
    
    // Add click event listener to reset score button
    const resetScoreBtn = document.getElementById('resetScoreBtn');
    if (resetScoreBtn) {
        resetScoreBtn.addEventListener('click', resetScores);
    }
    
    // Set initial game status
    status.textContent = "Your turn (X)";
}

// Start the game when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initGame();
});

// Check for fork opportunities
function checkForkOpportunity(board, pos, player) {
    if (board[pos] !== '') return false;
    
    board[pos] = player;
    let winningMoves = 0;
    
    // Check how many winning moves we would have after this move
    for (let i = 0; i < board.length; i++) {
        if (board[i] === '') {
            board[i] = player;
            if (checkWinForMinimax(board, player)) {
                winningMoves++;
            }
            board[i] = '';
        }
    }
    
    board[pos] = '';
    return winningMoves >= 2;
}

async function saveGameResult(result, moves) {
    try {
        const response = await fetch('/save-game-result', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'game_type': 'tictactoe',
                'result': result,
                'moves': JSON.stringify(moves)
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save game result');
        }
        
        const data = await response.json();
        console.log('Game result saved:', data.message);
    } catch (error) {
        console.error('Error saving game result:', error);
    }
}

// Check win for minimax
function checkWinForMinimax(board, player) {
    return winningConditions.some(condition => {
        return condition.every(index => board[index] === player);
    });
}

// Check draw for minimax
function checkDrawForMinimax(board) {
    return board.every(cell => cell !== '');
}

// Get game moves for saving
function getGameMoves() {
    // Create a copy of the current game state
    return [...gameState];
} 