public class PlayGame {

    private static  PlayGame startGame = null;
    public static PlayGame getPlayGame(){
        if(startGame == null)
         startGame = new PlayGame();
        return startGame;
    };

    public void startgame(){
        WheelOfFortune game = new WheelOfFortune();
        game.displayWelcomeMessage();

        Player player1 = new Player(1);
        do {
            if (game.playerEntered(player1)) break;

        }while(game.checkSolved()==false);
    }

}
