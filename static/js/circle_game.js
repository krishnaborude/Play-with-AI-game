document.addEventListener('DOMContentLoaded', () => {
    const gameBoard = document.getElementById('game-board');
    const startBtn = document.getElementById('start-btn');
    const resetBtn = document.getElementById('reset-btn');
    const scoreDisplay = document.getElementById('score');
    const timerDisplay = document.getElementById('timer');
    const gameOverlay = document.getElementById('game-overlay');
    const finalScoreDisplay = document.getElementById('final-score');
    const resultMessage = document.getElementById('result-message');
    const playAgainBtn = document.getElementById('play-again-btn');
    
    let score = 0;
    let timer = 30;
    let gameInterval;
    let timerInterval;
    let isGameActive = false;
    let startTime;
    
    function createCircle() {
        const circle = document.createElement('div');
        circle.className = 'circle';
        
        const size = Math.random() * 50 + 30;
        const x = Math.random() * (gameBoard.clientWidth - size);
        const y = Math.random() * (gameBoard.clientHeight - size);
        
        circle.style.width = `${size}px`;
        circle.style.height = `${size}px`;
        circle.style.left = `${x}px`;
        circle.style.top = `${y}px`;
        
        circle.addEventListener('click', () => {
            if (!isGameActive) return;
            score++;
            scoreDisplay.textContent = score;
            circle.remove();
        });
        
        gameBoard.appendChild(circle);
    }
    
    function startGame() {
        score = 0;
        timer = 30;
        scoreDisplay.textContent = score;
        timerDisplay.textContent = timer;
        isGameActive = true;
        gameOverlay.style.display = 'none';
        startTime = Date.now();  // Record start time
        
        gameInterval = setInterval(createCircle, 1000);
        timerInterval = setInterval(() => {
            timer--;
            timerDisplay.textContent = timer;
            
            if (timer <= 0) {
                endGame();
            }
        }, 1000);
        
        startBtn.disabled = true;
        resetBtn.disabled = false;
    }
    
    function showResults(result) {
        finalScoreDisplay.textContent = score;
        resultMessage.textContent = result === 'win' ? 'You won! 🎉' : 'Better luck next time!';
        gameOverlay.style.display = 'flex';
    }
    
    async function endGame() {
        isGameActive = false;
        clearInterval(gameInterval);
        clearInterval(timerInterval);
        startBtn.disabled = false;
        resetBtn.disabled = true;
        
        // Calculate time taken
        const timeTaken = (Date.now() - startTime) / 1000;  // Convert to seconds
        
        // Clear the game board and show the overlay immediately
        gameBoard.innerHTML = '';
        gameBoard.appendChild(gameOverlay);
        
        const result = score >= 10 ? 'win' : 'loss';
        showResults(result);  // Show results immediately
        
        try {
            const response = await fetch('/save-game-result', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `game_type=circle_game&result=${result}&moves=${score}&time_taken=${timeTaken}`
            });
            
            if (!response.ok) {
                throw new Error('Failed to save game result');
            }
        } catch (error) {
            console.error('Error saving game result:', error);
        }
    }
    
    function resetGame() {
        isGameActive = false;
        clearInterval(gameInterval);
        clearInterval(timerInterval);
        gameBoard.innerHTML = '';
        gameBoard.appendChild(gameOverlay);
        gameOverlay.style.display = 'none';
        score = 0;
        timer = 30;
        scoreDisplay.textContent = score;
        timerDisplay.textContent = timer;
        startBtn.disabled = false;
        resetBtn.disabled = true;
    }
    
    startBtn.addEventListener('click', startGame);
    resetBtn.addEventListener('click', resetGame);
    playAgainBtn.addEventListener('click', resetGame);
    
    // Initialize game state
    resetBtn.disabled = true;
}); 