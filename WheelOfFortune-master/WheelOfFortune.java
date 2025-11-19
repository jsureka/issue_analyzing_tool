import java.util.*;
public class WheelOfFortune 
{
	List<Choice> choiceMatcher = new ArrayList<Choice>(Arrays.<Choice>asList(new SpinChoice(), new GuessChoice()));
	private static GameBoard fortuneBoard = new GameBoard("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
					"The Secret Life of Bees", "Movies");

	public static void displayBoard()
	{
		fortuneBoard.displayLetters();
		fortuneBoard.updatePuzzle();
		fortuneBoard.displayPuzzle();
	}
	
	public void play (Player player)
	{
		int playerChoice=-1;
		boolean goAgain = true;
		Scanner keyboard;
		while (goAgain==true)
		{
			
			do
			{
				keyboard = new Scanner(System.in);
				try 
				{
					System.out.print("Player " + player.getPlayerNumber() + " - would you like to Spin (1)"
						+ " or Guess (2) the puzzle? ");
					playerChoice = keyboard.nextInt();
					
				}
				catch (InputMismatchException e)
				{
					playerChoice=-1;
				}
				
			}while(playerChoice != 1 && playerChoice!=2);
			
			for(Choice makeChoice: choiceMatcher )
			{
				if(makeChoice.selectedChoice(playerChoice))
					makeChoice.operation(player,fortuneBoard,goAgain);
			}

			if(checkSolved()==true)
			{
				
				goAgain=false;
				System.out.println("Congratulations! You Solved the Puzzle!\n"+
							"Player " + player.getPlayerNumber()+ " Wins!");
			}
		}
		
	}//End Play
	
	public static boolean checkSolved()
	{
		boolean solved;
		if (fortuneBoard.getPendingPuzzle().equalsIgnoreCase(fortuneBoard.getPuzzle())) {
			solved = true;
			
		}
		else
			solved =  false;
		
		return solved;
	}


	  boolean playerEntered(Player player) {
		displayBoard();
		play(player);

		if (checkSolved())
			return true;
		return false;
	}

		 void displayWelcomeMessage() {
		System.out.println("Welcome to the Wheel of Fortune\n");
	}


}
