import java.util.Scanner;

public class SpinChoice implements Choice{
    Wheel fortuneWheel = new Wheel();
    Scanner keyboard;
    @Override
    public boolean selectedChoice(int choice) {
        return choice==1;
    }

    @Override
    public void operation(Player player, GameBoard fortuneBoard, boolean goAgain) {
        keyboard = new Scanner(System.in);
        fortuneWheel.spin();
        if (hasValidWheelValue())
        {
            makeGuess(player, fortuneBoard);
            fortuneBoard.setCharacter(player.getPlayerGuess());
            System.out.println();
            fortuneBoard.updateAvailableLetters();
            boolean isCorrectGuess = fortuneBoard.isLetterInPuzzle(player.getPlayerGuess());

            if (isCorrectGuess)
                WheelOfFortune.displayBoard();
            else {
                goAgain=false;
                System.out.println("Incorrect!");
                System.out.println();
            }

        }

        else
        {
            goAgain = false;
        }
    }

    private boolean hasValidWheelValue() {
        return fortuneWheel.getWheelValue() > 0.0;
    }

    private void makeGuess(Player player, GameBoard fortuneBoard) {
        boolean wasGuessed;
        do
        {
            System.out.print("Select your letter from the available letters from above: ");
            player.setPlayerGuess(keyboard.next().charAt(0));
            wasGuessed = fortuneBoard.isLetterGuessed(player.getPlayerGuess());

        }while (wasGuessed);
    }
}
